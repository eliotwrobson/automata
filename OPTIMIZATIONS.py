"""
Optimization Summary for DFA Minimization

This document describes the optimizations made to improve performance
of the Valmari algorithm implementation.
"""

# OPTIMIZATION 1: Block Size Caching
# ===================================
# Problem: The code was calling len(blocks.get_set_by_id(...)) repeatedly
# for the same block IDs, which involves dictionary lookups and set iteration.
# 
# Solution: Cache block sizes in a dictionary:
#   block_sizes: Dict[int, int] = {}
# 
# Impact: Eliminates repeated len() calls, especially important when
# comparing sizes of new blocks multiple times.

# OPTIMIZATION 2: Inverse Worklist Mapping  
# =========================================
# Problem: When updating the worklist after a block split, the old code
# iterated through ALL input symbols (potentially 100+) to check if each
# symbol's worklist contained the split block:
#
#   for sym in input_symbols:  # O(α) where α = alphabet size
#       if check_block_id in worklist[sym]:  # Set membership check
#           ...
#
# With 100-250 symbols and many block splits, this becomes expensive.
#
# Solution: Maintain an inverse mapping:
#   block_to_symbols: Dict[int, Set[str]] = defaultdict(set)
#
# This tracks which symbols have each block in their worklist.
# Now we can directly look up: symbols_with_block = block_to_symbols[check_block_id]
#
# Impact: Changes O(α) iteration to O(1) lookup for each block split.
# For large alphabets (α=100-250), this is a significant improvement.

# OPTIMIZATION 3: Combined Size Computation
# =========================================
# Problem: Computing new_size and remaining_size separately required
# two get_set_by_id() calls.
#
# Solution: Compute both sizes once and cache them immediately.
#
# Impact: Reduces get_set_by_id calls by ~50% during refinement.

# EXPECTED PERFORMANCE IMPROVEMENTS
# ==================================
# These optimizations particularly benefit:
# 1. Large alphabets (100+ symbols) - inverse mapping avoids O(α) iterations
# 2. Many block splits - size caching eliminates redundant computations  
# 3. Large state spaces - fewer dictionary/set operations overall
#
# Conservative estimate: 10-20% speedup on large DFAs with large alphabets
# Best case: 30-40% speedup when alphabet is very large (200+ symbols)

print(__doc__)
