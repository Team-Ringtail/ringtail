# LeetCode Benchmarks

Benchmark inputs for the optimization loop: each problem has a reference (unoptimized) solution and test cases. The harness runs a solution (reference or optimized) against these tests and reports correctness and timing.

## Problem subset

| Slug | LC # | Title | Difficulty |
|------|------|-------|------------|
| two_sum | 1 | Two Sum | easy |
| three_sum | 15 | 3Sum | medium |
| three_sum_closest | 16 | 3Sum Closest | medium |
| four_sum | 18 | 4Sum | medium |
| add_digits | 258 | Add Digits | easy |
| additive_number | 306 | Additive Number | medium |
| burst_balloons | 312 | Burst Balloons | hard |
| combination_sum_ii | 40 | Combination Sum II | medium |
| container_with_most_water | 11 | Container With Most Water | medium |
| convert_sorted_list_to_bst | 109 | Convert Sorted List to BST | medium |
| count_smaller_after_self | 315 | Count of Smaller Numbers After Self | hard |
| delete_node_in_linked_list | 237 | Delete Node in a Linked List | easy |
| divide_two_integers | 29 | Divide Two Integers | medium |
| search_range | 34 | Find First and Last Position in Sorted Array | medium |
| find_min_rotated | 153 | Find Minimum in Rotated Sorted Array | medium |
| find_peak_element | 162 | Find Peak Element | medium |
| gray_code | 89 | Gray Code | medium |
| integer_to_roman | 12 | Integer to Roman | medium |
| kth_smallest_sorted_matrix | 378 | Kth Smallest in Sorted Matrix | medium |
| largest_number | 179 | Largest Number | medium |
| longest_increasing_subsequence | 300 | Longest Increasing Subsequence | medium |
| longest_palindromic_substring | 5 | Longest Palindromic Substring | medium |
| longest_substring_no_repeat | 3 | Longest Substring Without Repeating Characters | medium |
| lru_cache | 146 | LRU Cache | medium |
| merge_intervals | 56 | Merge Intervals | medium |
| min_stack | 155 | Min Stack | easy |
| nim_game | 292 | Nim Game | easy |
| n_queens | 51 | N-Queens | hard |
| n_queens_ii | 52 | N-Queens II | hard |
| number_of_1_bits | 191 | Number of 1 Bits | easy |
| palindrome_number | 9 | Palindrome Number | easy |
| pascals_triangle | 118 | Pascal's Triangle | easy |
| permutation_sequence | 60 | Permutation Sequence | hard |
| permutations | 46 | Permutations | medium |
| permutations_ii | 47 | Permutations II | medium |
| pow_x_n | 50 | Pow(x, n) | medium |
| power_of_two | 231 | Power of Two | easy |
| rectangle_area | 223 | Rectangle Area | medium |
| remove_invalid_parentheses | 301 | Remove Invalid Parentheses | hard |
| remove_nth_from_end | 19 | Remove Nth Node From End of List | medium |
| restore_ip_addresses | 93 | Restore IP Addresses | medium |
| reverse_bits | 190 | Reverse Bits | easy |
| reverse_integer | 7 | Reverse Integer | easy |
| reverse_nodes_k_group | 25 | Reverse Nodes in k-Group | hard |
| roman_to_integer | 13 | Roman to Integer | easy |
| rotate_image | 48 | Rotate Image | medium |
| russian_doll_envelopes | 354 | Russian Doll Envelopes | hard |
| search_rotated_sorted_array | 33 | Search in Rotated Sorted Array | medium |
| search_insert_position | 35 | Search Insert Position | easy |
| sort_list | 148 | Sort List | medium |
| spiral_matrix_ii | 59 | Spiral Matrix II | medium |
| sqrt_x | 69 | Sqrt(x) | easy |
| string_to_integer_atoi | 8 | String to Integer (atoi) | medium |
| subsets | 78 | Subsets | medium |
| subsets_ii | 90 | Subsets II | medium |
| swap_nodes_in_pairs | 24 | Swap Nodes in Pairs | medium |
| skyline_problem | 218 | The Skyline Problem | hard |
| valid_parentheses | 20 | Valid Parentheses | easy |
| valid_sudoku | 36 | Valid Sudoku | medium |
| zigzag_conversion | 6 | Zigzag Conversion | medium |

## Structure (per problem)

Each problem lives under `benchmarks/leetcode/<slug>/`:

- **spec.json** — Problem id, title, difficulty, expected complexity (for comparison).
- **solution.py** — Reference (unoptimized) solution. Must expose the function the tests call (see test file).
- **test_<slug>.py** — Pytest tests. Import the solution from the path in env `BENCHMARK_SOLUTION` (default: `solution` in same dir), so the same tests run against reference or optimized code.

## Running a single benchmark

From repo root:

```bash
python benchmarks/run_benchmark.py <slug>
```

Example: `python benchmarks/run_benchmark.py two_sum`

Output: JSON with `passed`, `failed`, `time_seconds`, and optional error details.

## Running all LeetCode benchmarks

```bash
python benchmarks/run_benchmark.py --all
```
