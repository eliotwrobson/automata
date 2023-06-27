# Can build this file with the following command:
# python setup.py build_ext --inplace
# Then, simply run the tests by using the command:
# nose2

#TODO this class is no longer used externally, can be converted for internal use only (no Python callouts).
cdef class PartitionRefinement:
    """Maintain and refine a partition of a set of items into subsets.
    Space usage for a partition of n items is O(n), and each refine operation
    takes time proportional to the size of its argument.

    Adapted from code by D. Eppstein:
    https://www.ics.uci.edu/~eppstein/PADS/PartitionRefinement.py
    """

    #__slots__ = ("_sets", "_partition")

    #_sets: Dict[int, Set[T]]
    #_partition: Dict[T, int]

    cdef dict _sets
    cdef dict _partition

    def __init__(self, items):
        """Create a new partition refinement data structure for the given
        items. Initially, all items belong to the same subset.
        """
        cdef set S = set(items)
        self._sets = {id(S): S}
        self._partition = {x: id(S) for x in S}

    cdef set get_set_by_id(self, long long id):
        """Return the set in the partition corresponding to id."""
        return self._sets[id]

    cdef get_set_ids(self):
        """Return set ids corresponding to the internal partition."""
        return self._sets.keys()

    def get_sets(self):
        """Return sets corresponding to the internal partition."""
        return self._sets.values()

    cdef tuple refine(self, set S):
        """Refine each set A in the partition to the two sets
        A & S, A - S.  Return a list of pairs ids (id(A & S), id(A - S))
        for each changed set.  Within each pair, A & S will be
        a newly created set, while A - S will be a modified
        version of an existing set in the partition (retaining its old id).
        Not a generator because we need to perform the partition
        even if the caller doesn't iterate through the results.
        """

        # TODO this hit dict doesn't get read externally, should be a way to change
        # this to a pure C data structure to prevent more calls to the python interpreter
        cdef dict hit = dict()
        cdef long long partition_id
        cdef set temp

        for x in S:
            partition_id = self._partition[x]

            if partition_id not in hit:
                temp = {x}
                hit[partition_id] = temp
            else:
                temp = hit[partition_id]
                temp.add(x)

        cdef list new_sets = []
        cdef list old_sets = []

        cdef set A
        cdef set AintS
        cdef long long AintS_id
        for Aid, AintS in hit.items():
            A = self._sets[Aid]

            # Only need to check lengths, we already know AintS is a subset of A
            # by construction
            if len(AintS) < len(A):
                AintS_id = id(AintS)
                self._sets[AintS_id] = AintS
                for x in AintS:
                    self._partition[x] = AintS_id
                A -= AintS

                new_sets.append(AintS_id)
                old_sets.append(Aid)

        return new_sets, old_sets


def _minify_worker(
    reachable_states_input,
    input_symbols_input,
    transitions_input,
    reachable_final_states_input,
):

    # Redeclare everything statically because of the more abstract interface
    cdef frozenset reachable_states = frozenset(reachable_states_input)
    cdef frozenset input_symbols = frozenset(input_symbols_input)
    cdef dict transitions = dict(transitions_input)
    cdef set reachable_final_states = set(reachable_final_states_input)

    # First, assemble backmap and equivalence class data structure
    cdef PartitionRefinement eq_classes = PartitionRefinement(reachable_states)
    refinement, _ = eq_classes.refine(reachable_final_states)

    cdef long long final_states_id = (
        refinement[0] if refinement else next(iter(eq_classes.get_set_ids()))
    )

    #  Dict[str, Dict[DFAStateT, List[DFAStateT]]]
    cdef dict transition_back_map = {
        symbol: {end_state: list() for end_state in reachable_states}
        for symbol in input_symbols
    }

    for start_state, path in transitions.items():
        if start_state in reachable_states:
            for symbol, end_state in path.items():
                transition_back_map[symbol][end_state].append(start_state)

    cdef tuple origin_dicts = tuple(transition_back_map.values())
    cdef set processing = {final_states_id}

    # Statically declare variables we'll use later
    cdef tuple active_state
    cdef long long YintX_id
    cdef long long YdiffX_id
    cdef tuple new_eq_class_lists
    cdef dict origin_dict

    cdef list YintX_list
    cdef list YdiffX_list
    cdef int i

    cdef set states_that_move_into_active_state
    cdef list origin_list

    while processing:
        # Save a copy of the set, since it could get modified while executing
        active_state = tuple(eq_classes.get_set_by_id(processing.pop()))
        for origin_dict in origin_dicts:
            states_that_move_into_active_state = set()

            for end_state in active_state:
                origin_list = origin_dict[end_state]
                states_that_move_into_active_state.update(origin_list)


            # Refine set partition by states moving into current active one
            new_eq_class_lists = eq_classes.refine(
                states_that_move_into_active_state
            )

            YintX_list, YdiffX_list = new_eq_class_lists

            for i in range(len(YintX_list)):
                YintX_id = YintX_list[i]
                YdiffX_id = YdiffX_list[i]

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

    return eq_classes.get_sets()
