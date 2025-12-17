"""
Performance comparison between old (Hopcroft) and new (Valmari) DFA minimization algorithms.

This script generates large random partial DFAs and compares the time taken to minify them
using both the old and new implementations.
"""

import random
import time
from itertools import chain, count
from typing import AbstractSet, Dict, List, Set, Tuple, Type, TypeVar

from automata.base.utils import PartitionRefinement
from automata.fa.dfa import DFA, DFAStateT, DFATransitionsT

Self = TypeVar("Self", bound="DFA")


def generate_random_partial_dfa(
    num_states: int,
    alphabet_size: int,
    transition_density: float = 0.7,
    final_state_ratio: float = 0.3,
) -> DFA:
    """
    Generate a random partial DFA for testing.

    Parameters:
    - num_states: Number of states in the DFA
    - alphabet_size: Size of the input alphabet
    - transition_density: Probability that a transition exists (0.0 to 1.0)
    - final_state_ratio: Ratio of states that are final states

    Returns a random partial DFA
    """
    states = set(range(num_states))
    input_symbols = set(chr(ord("a") + i) for i in range(alphabet_size))
    initial_state = 0

    # Random final states
    num_final = max(1, int(num_states * final_state_ratio))
    final_states = set(random.sample(list(states), num_final))

    # Generate transitions with given density
    transitions = {}
    for state in states:
        state_transitions = {}
        for symbol in input_symbols:
            if random.random() < transition_density:
                # Add transition to a random state
                target = random.choice(list(states))
                state_transitions[symbol] = target
        transitions[state] = state_transitions

    return DFA(
        states=states,
        input_symbols=input_symbols,
        transitions=transitions,
        initial_state=initial_state,
        final_states=final_states,
        allow_partial=True,
    )


def generate_highly_reducible_dfa(
    num_equivalent_groups: int,
    states_per_group: int,
    alphabet_size: int,
    transition_density: float = 0.8,
) -> DFA:
    """
    Generate a DFA with many equivalent states that should be merged during minimization.
    This creates groups of states that behave identically, providing high reduction potential.

    Parameters:
    - num_equivalent_groups: Number of distinct behavior groups
    - states_per_group: Number of equivalent states in each group
    - alphabet_size: Size of the input alphabet
    - transition_density: Probability that a transition exists (0.0 to 1.0)

    Returns a DFA with many mergeable states
    """
    total_states = num_equivalent_groups * states_per_group
    states = set(range(total_states))
    input_symbols = set(chr(ord("a") + i) for i in range(alphabet_size))
    initial_state = 0

    # Each group has the same final state property
    final_states = set()
    for group_id in range(num_equivalent_groups):
        if group_id % 2 == 0:  # Every other group is final
            for i in range(states_per_group):
                state_id = group_id * states_per_group + i
                final_states.add(state_id)

    # Generate transitions where all states in a group behave identically
    transitions = {}
    group_behaviors = []  # Store the transition behavior for each group

    for group_id in range(num_equivalent_groups):
        # Define the behavior for this group
        group_behavior = {}
        for symbol in input_symbols:
            if random.random() < transition_density:
                # Pick a random target group
                target_group = random.randint(0, num_equivalent_groups - 1)
                # Pick the first state in that group as representative
                target_state = target_group * states_per_group
                group_behavior[symbol] = target_group
            else:
                group_behavior[symbol] = None  # Missing transition
        group_behaviors.append(group_behavior)

    # Apply the same behavior to all states in each group
    for group_id in range(num_equivalent_groups):
        group_behavior = group_behaviors[group_id]
        for i in range(states_per_group):
            state_id = group_id * states_per_group + i
            state_transitions = {}
            for symbol, target_group in group_behavior.items():
                if target_group is not None:
                    # Map to a random state in the target group (they're all equivalent)
                    target_state = target_group * states_per_group + random.randint(
                        0, states_per_group - 1
                    )
                    state_transitions[symbol] = target_state
            transitions[state_id] = state_transitions

    return DFA(
        states=states,
        input_symbols=input_symbols,
        transitions=transitions,
        initial_state=initial_state,
        final_states=final_states,
        allow_partial=True,
    )


def old_minify_hopcroft(
    cls: Type[DFA],
    *,
    reachable_states: AbstractSet[DFAStateT],
    input_symbols: AbstractSet[str],
    transitions: DFATransitionsT,
    initial_state: DFAStateT,
    reachable_final_states: AbstractSet[DFAStateT],
    retain_names: bool,
) -> DFA:
    """
    Old Hopcroft-based minify implementation from commit d08ccbf.
    """
    reachable_states = set(reachable_states)

    # Per input-symbol backmap (tgt -> origin states)
    transition_back_map: Dict[str, Dict[DFAStateT, List[DFAStateT]]] = {
        symbol: {end_state: [] for end_state in reachable_states}
        for symbol in input_symbols
    }

    trap_state = None

    for start_state, path in transitions.items():
        if start_state in reachable_states:
            for symbol in input_symbols:
                end_state = path.get(symbol)

                # If statement here needed to ignore certain transitions
                # for non-reachable states
                if end_state in reachable_states:
                    symbol_dict = transition_back_map[symbol]
                    symbol_dict[end_state].append(start_state)
                else:
                    # Add trap state if needed
                    if trap_state is None:
                        trap_state = next(
                            x for x in count(-1, -1) if x not in reachable_states
                        )
                        for trap_symbol in input_symbols:
                            transition_back_map[trap_symbol][trap_state] = [trap_state]

                        reachable_states.add(trap_state)

                    transition_back_map[symbol][trap_state].append(start_state)

    # Set up equivalence class data structure
    eq_classes = PartitionRefinement(reachable_states)
    refinement = eq_classes.refine(reachable_final_states)

    final_states_id = (
        refinement[0][0] if refinement else next(iter(eq_classes.get_set_ids()))
    )

    origin_dicts = tuple(transition_back_map.values())
    processing = {final_states_id}

    while processing:
        # Save a copy of the set, since it could get modified while executing
        active_state = tuple(eq_classes.get_set_by_id(processing.pop()))
        for origin_dict in origin_dicts:
            states_that_move_into_active_state = chain.from_iterable(
                origin_dict[end_state] for end_state in active_state
            )

            # Refine set partition by states moving into current active one
            new_eq_class_pairs = eq_classes.refine(states_that_move_into_active_state)

            for YintX_id, YdiffX_id in new_eq_class_pairs:
                # Only adding one id to processing, since the other is already there
                if YdiffX_id in processing:
                    processing.add(YintX_id)
                else:
                    if len(eq_classes.get_set_by_id(YintX_id)) <= len(
                        eq_classes.get_set_by_id(YdiffX_id)
                    ):
                        processing.add(YintX_id)
                    else:
                        processing.add(YdiffX_id)

    # now eq_classes are good to go, make them a list for ordering
    eq_class_name_pairs: List[Tuple[DFAStateT, Set[DFAStateT]]] = (
        [(frozenset(eq), eq) for eq in eq_classes.get_sets()]
        if retain_names
        else list(enumerate(eq_classes.get_sets()))
    )

    # need a backmap to prevent constant calls to index
    back_map = {
        state: name
        for name, eq in eq_class_name_pairs
        for state in eq
        if trap_state not in eq
    }

    # If only one equivalence class with the trap state,
    # return empty language.
    if not back_map:
        return cls.empty_language(input_symbols)

    new_input_symbols = input_symbols
    new_states = frozenset(back_map.values())
    new_initial_state = back_map[initial_state]
    new_final_states = frozenset(back_map[acc] for acc in reachable_final_states)
    new_transitions = {}

    for name, eq in eq_class_name_pairs:
        # For trap state, can just leave out
        if trap_state in eq:
            continue

        eq_class_rep = next(iter(eq))

        inner_transition_dict_old = transitions[eq_class_rep]
        new_transitions[name] = {
            letter: back_map[inner_transition_dict_old[letter]]
            for letter in inner_transition_dict_old.keys()
            if inner_transition_dict_old[letter] in back_map.keys()
        }

    allow_partial = any(
        len(lookup) != len(input_symbols) for lookup in new_transitions.values()
    )
    return cls(
        states=new_states,
        input_symbols=new_input_symbols,
        transitions=new_transitions,
        initial_state=new_initial_state,
        final_states=new_final_states,
        allow_partial=allow_partial,
    )


def benchmark_minify_algorithms(
    num_states: int, alphabet_size: int, num_trials: int = 3
):
    """
    Benchmark the old and new minify algorithms on random partial DFAs.

    Parameters:
    - num_states: Number of states in the test DFA
    - alphabet_size: Size of the input alphabet
    - num_trials: Number of trials to average over
    """
    print(f"\n{'=' * 80}")
    print(f"Benchmarking with {num_states} states and alphabet size {alphabet_size}")
    print(f"{'=' * 80}\n")

    old_times = []
    new_times = []

    for trial in range(num_trials):
        print(f"Trial {trial + 1}/{num_trials}:")

        # Generate random DFA
        dfa = generate_random_partial_dfa(num_states, alphabet_size)

        # Count transitions
        num_transitions = sum(len(trans) for trans in dfa.transitions.values())

        print(
            f"  Original DFA: {len(dfa.states)} states, {num_transitions} transitions, {len(dfa.final_states)} final states"
        )

        # Get reachable states for both algorithms
        if dfa.allow_partial:
            graph = dfa._get_digraph()
            from automata.base.utils import get_reachable_nodes

            live_states = get_reachable_nodes(graph, [dfa.initial_state])
            non_trap_states = get_reachable_nodes(
                graph, dfa.final_states, reversed=True
            )
            reachable_states = live_states & non_trap_states
            reachable_states.add(dfa.initial_state)
        else:
            bfs_states = DFA._bfs_states(
                dfa.initial_state, lambda state: iter(dfa.transitions[state].items())
            )
            reachable_states = set(bfs_states)

        reachable_final_states = dfa.final_states & reachable_states

        # Benchmark old algorithm (Hopcroft)
        start_time = time.perf_counter()
        old_result = old_minify_hopcroft(
            DFA,
            reachable_states=reachable_states,
            input_symbols=dfa.input_symbols,
            transitions=dfa.transitions,
            initial_state=dfa.initial_state,
            reachable_final_states=reachable_final_states,
            retain_names=False,
        )
        old_time = time.perf_counter() - start_time
        old_times.append(old_time)

        old_num_transitions = sum(
            len(trans) for trans in old_result.transitions.values()
        )
        print(
            f"  Old (Hopcroft): {old_time * 1000:.2f}ms -> {len(old_result.states)} states, {old_num_transitions} transitions"
        )

        # Benchmark new algorithm (Valmari)
        start_time = time.perf_counter()
        new_result = DFA._minify(
            reachable_states=reachable_states,
            input_symbols=dfa.input_symbols,
            transitions=dfa.transitions,
            initial_state=dfa.initial_state,
            reachable_final_states=reachable_final_states,
            retain_names=False,
        )
        new_time = time.perf_counter() - start_time
        new_times.append(new_time)

        new_num_transitions = sum(
            len(trans) for trans in new_result.transitions.values()
        )
        print(
            f"  New (Valmari): {new_time * 1000:.2f}ms -> {len(new_result.states)} states, {new_num_transitions} transitions"
        )

        # Check if new algorithm is incorrectly adding transitions
        if new_num_transitions > old_num_transitions:
            print(
                f"  ⚠️  WARNING: New algorithm added transitions! ({new_num_transitions} vs {old_num_transitions})"
            )
        elif new_num_transitions < old_num_transitions:
            print(
                f"  ⚠️  WARNING: New algorithm has fewer transitions! ({new_num_transitions} vs {old_num_transitions})"
            )

        # Verify results are equivalent
        if old_result != new_result:
            print("  ⚠️  WARNING: Results are not equivalent!")
        else:
            print("  ✓ Results are equivalent")

        speedup = old_time / new_time if new_time > 0 else float("inf")
        print(f"  Speedup: {speedup:.2f}x")
        print()

    # Print summary
    avg_old = sum(old_times) / len(old_times)
    avg_new = sum(new_times) / len(new_times)
    avg_speedup = avg_old / avg_new if avg_new > 0 else float("inf")

    print(f"{'=' * 80}")
    print(f"Summary ({num_trials} trials):")
    print(f"  Old (Hopcroft) average: {avg_old * 1000:.2f}ms")
    print(f"  New (Valmari) average: {avg_new * 1000:.2f}ms")
    print(f"  Average speedup: {avg_speedup:.2f}x")
    print(f"{'=' * 80}\n")


def benchmark_reducible_dfas(
    num_equivalent_groups: int,
    states_per_group: int,
    alphabet_size: int,
    num_trials: int = 3,
):
    """
    Benchmark on highly reducible DFAs where many states should be merged.

    Parameters:
    - num_equivalent_groups: Number of distinct behavior groups
    - states_per_group: Number of equivalent states in each group
    - alphabet_size: Size of the input alphabet
    - num_trials: Number of trials to average over
    """
    total_states = num_equivalent_groups * states_per_group
    print(f"\n{'=' * 80}")
    print(
        f"Benchmarking HIGHLY REDUCIBLE DFAs: {total_states} states ({num_equivalent_groups} groups × {states_per_group} states/group)"
    )
    print(f"Alphabet size: {alphabet_size}")
    print(f"Expected reduction: {total_states} → ~{num_equivalent_groups} states")
    print(f"{'=' * 80}\n")

    old_times = []
    new_times = []
    reduction_ratios = []

    for trial in range(num_trials):
        print(f"Trial {trial + 1}/{num_trials}:")

        # Generate highly reducible DFA
        print(f"  Generating DFA with {total_states:,} states...", end=" ", flush=True)
        dfa = generate_highly_reducible_dfa(
            num_equivalent_groups, states_per_group, alphabet_size
        )

        # Count transitions
        num_transitions = sum(len(trans) for trans in dfa.transitions.values())

        print("done")
        print(
            f"  Original DFA: {len(dfa.states):,} states, {num_transitions:,} transitions"
        )

        # Get reachable states
        if dfa.allow_partial:
            graph = dfa._get_digraph()
            from automata.base.utils import get_reachable_nodes

            live_states = get_reachable_nodes(graph, [dfa.initial_state])
            non_trap_states = get_reachable_nodes(
                graph, dfa.final_states, reversed=True
            )
            reachable_states = live_states & non_trap_states
            reachable_states.add(dfa.initial_state)
        else:
            bfs_states = DFA._bfs_states(
                dfa.initial_state, lambda state: iter(dfa.transitions[state].items())
            )
            reachable_states = set(bfs_states)

        reachable_final_states = dfa.final_states & reachable_states

        # Benchmark old algorithm
        print("  Running old (Hopcroft) algorithm...", end=" ", flush=True)
        start_time = time.perf_counter()
        old_result = old_minify_hopcroft(
            DFA,
            reachable_states=reachable_states,
            input_symbols=dfa.input_symbols,
            transitions=dfa.transitions,
            initial_state=dfa.initial_state,
            reachable_final_states=reachable_final_states,
            retain_names=False,
        )
        old_time = time.perf_counter() - start_time
        old_times.append(old_time)

        old_num_transitions = sum(
            len(trans) for trans in old_result.transitions.values()
        )
        reduction = (
            len(dfa.states) / len(old_result.states)
            if len(old_result.states) > 0
            else 1
        )
        print(
            f"done in {old_time:.2f}s -> {len(old_result.states):,} states ({reduction:.1f}× reduction), {old_num_transitions:,} transitions"
        )

        # Benchmark new algorithm
        print("  Running new (Valmari) algorithm...", end=" ", flush=True)
        start_time = time.perf_counter()
        new_result = DFA._minify(
            reachable_states=reachable_states,
            input_symbols=dfa.input_symbols,
            transitions=dfa.transitions,
            initial_state=dfa.initial_state,
            reachable_final_states=reachable_final_states,
            retain_names=False,
        )
        new_time = time.perf_counter() - start_time
        new_times.append(new_time)

        new_num_transitions = sum(
            len(trans) for trans in new_result.transitions.values()
        )
        print(
            f"done in {new_time:.2f}s -> {len(new_result.states):,} states, {new_num_transitions:,} transitions"
        )

        reduction_ratios.append(reduction)

        # Check for transition mismatches
        if new_num_transitions != old_num_transitions:
            print(
                f"  ⚠️  TRANSITION MISMATCH: {new_num_transitions} vs {old_num_transitions}"
            )

        # Verify equivalence
        if old_result != new_result:
            print("  ⚠️  WARNING: Results are not equivalent!")
        else:
            print("  ✓ Results are equivalent")

        speedup = old_time / new_time if new_time > 0 else float("inf")
        print(f"  Speedup: {speedup:.2f}x")
        print()

    # Print summary
    avg_old = sum(old_times) / len(old_times)
    avg_new = sum(new_times) / len(new_times)
    avg_speedup = avg_old / avg_new if avg_new > 0 else float("inf")
    avg_reduction = sum(reduction_ratios) / len(reduction_ratios)

    print(f"{'=' * 80}")
    print(f"Summary ({num_trials} trials):")
    print(
        f"  Average reduction: {avg_reduction:.1f}× ({total_states:,} → ~{total_states / avg_reduction:.0f} states)"
    )
    # Use seconds or milliseconds depending on magnitude
    if avg_old < 1.0:
        print(f"  Old (Hopcroft) average: {avg_old * 1000:.2f}ms")
        print(f"  New (Valmari) average: {avg_new * 1000:.2f}ms")
    else:
        print(f"  Old (Hopcroft) average: {avg_old:.2f}s")
        print(f"  New (Valmari) average: {avg_new:.2f}s")
    print(f"  Average speedup: {avg_speedup:.2f}x")
    if avg_speedup > 1.0:
        print(f"  ✅ New algorithm is FASTER by {(avg_speedup - 1) * 100:.1f}%")
    else:
        print(f"  ⚠️  New algorithm is slower by {(1 - avg_speedup) * 100:.1f}%")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    random.seed(42)  # For reproducibility

    print("DFA Minimization Algorithm Performance Comparison")
    print("Old: Hopcroft algorithm (commit d08ccbf)")
    print("New: Valmari algorithm (current implementation)\n")

    # Uncomment to run smaller tests
    # print("\n" + "=" * 80)
    # print("PART 1: Random Partial DFAs (low reduction potential)")
    # print("=" * 80)

    # # Test with random partial DFAs
    # test_cases = [
    #     (100, 10),  # 100 states, 10 symbols
    #     (500, 20),  # 500 states, 20 symbols
    #     (1000, 50),  # 1000 states, 50 symbols
    #     (2000, 100),  # 2000 states, 100 symbols (large alphabet)
    # ]

    # for num_states, alphabet_size in test_cases:
    #     benchmark_minify_algorithms(num_states, alphabet_size, num_trials=3)

    # print("\n" + "=" * 80)
    # print("PART 2: Highly Reducible DFAs (high reduction potential)")
    # print("=" * 80)

    # # Test with highly reducible DFAs - where Valmari's algorithm should shine
    # reducible_test_cases = [
    #     (20, 10, 10),  # 200 states (20 groups × 10 states), 10 symbols
    #     (50, 20, 20),  # 1000 states (50 groups × 20 states), 20 symbols
    #     (100, 50, 50),  # 5000 states (100 groups × 50 states), 50 symbols
    #     (200, 100, 100),  # 20000 states (200 groups × 100 states), 100 symbols
    # ]

    # for num_groups, states_per_group, alphabet_size in reducible_test_cases:
    #     benchmark_reducible_dfas(
    #         num_groups, states_per_group, alphabet_size, num_trials=3
    #     )

    print("\n" + "=" * 80)
    print("PART 3: VERY LARGE Highly Reducible DFAs (100K - 500K states)")
    print("=" * 80)
    print("These tests will take several minutes each...")

    # Very large DFAs - single trial each due to time
    # Note: using fewer states per group for faster generation
    very_large_test_cases = [
        (500, 200, 150),  # 100K states (500 groups × 200 states), 150 symbols
        (1000, 200, 200),  # 200K states (1000 groups × 200 states), 200 symbols
        (2000, 250, 250),  # 500K states (2000 groups × 250 states), 250 symbols
    ]

    for num_groups, states_per_group, alphabet_size in very_large_test_cases:
        benchmark_reducible_dfas(
            num_groups, states_per_group, alphabet_size, num_trials=1
        )

    print("\nBenchmark complete!")
