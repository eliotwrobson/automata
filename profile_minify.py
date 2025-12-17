"""Quick profile to see where time is spent in new minify."""

import cProfile
import pstats
from io import StringIO

from automata.base.utils import get_reachable_nodes
from automata.fa.dfa import DFA
from benchmark_minify import generate_random_partial_dfa

# Generate a test DFA
dfa = generate_random_partial_dfa(200, 20)

# Get reachable states
graph = dfa._get_digraph()
live_states = get_reachable_nodes(graph, [dfa.initial_state])
non_trap_states = get_reachable_nodes(graph, dfa.final_states, reversed=True)
reachable_states = live_states & non_trap_states
reachable_states.add(dfa.initial_state)
reachable_final_states = dfa.final_states & reachable_states

print(
    f"DFA: {len(reachable_states)} reachable states, {len(dfa.input_symbols)} symbols"
)

# Profile the new implementation
profiler = cProfile.Profile()
profiler.enable()

result = DFA._minify(
    reachable_states=reachable_states,
    input_symbols=dfa.input_symbols,
    transitions=dfa.transitions,
    initial_state=dfa.initial_state,
    reachable_final_states=reachable_final_states,
    retain_names=False,
)

profiler.disable()

# Print profile stats
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
ps.print_stats(20)
print(s.getvalue())

print(f"\nResult: {len(result.states)} states")
