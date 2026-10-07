# Merge Sort - Railway Passenger Age Sorting

A Python program that sorts passenger ages in ascending order using **Merge Sort** (Divide-and-Conquer) and compares the number of comparisons made for three types of input.

## Problem Statement

An Indian railway reservation system stores the ages of passengers who booked tickets for a particular train. The system needs to arrange the ages in ascending order for statistical analysis.

**Task:** Implement Merge Sort using Divide-and-Conquer.

**Additional requirement:** Compare the number of comparisons for:
- Already sorted input
- Reverse sorted input
- Random input

Also determine the time complexity for each case.

## How It Works

Merge Sort follows three steps:

1. **Divide** - split the list into two halves at the middle.
2. **Conquer** - sort each half recursively until a list has 0 or 1 element.
3. **Combine** - merge the two sorted halves into one sorted list.

Every time two ages are compared inside the merge step, a counter is increased. The final count shows how much work the algorithm did.

## Requirements

- Python 3.x
- No external libraries needed

## How to Run

```bash
python merge_sort.py
```

Enter the passenger ages separated by spaces when asked.

## Sample Input and Output

**Input**

```
Enter passenger ages separated by space: 45 23 67 12 34 56 29 41
```

**Output**

```
Random Input (as entered)
Input  : [45, 23, 67, 12, 34, 56, 29, 41]
Output : [12, 23, 29, 34, 41, 45, 56, 67]
Comparisons: 17
Time Complexity: O(n log n)

Already Sorted Input
Input  : [12, 23, 29, 34, 41, 45, 56, 67]
Output : [12, 23, 29, 34, 41, 45, 56, 67]
Comparisons: 12
Time Complexity: O(n log n)

Reverse Sorted Input
Input  : [67, 56, 45, 41, 34, 29, 23, 12]
Output : [12, 23, 29, 34, 41, 45, 56, 67]
Comparisons: 12
Time Complexity: O(n log n)
```

## Results

| Case | Comparisons (8 ages) | Time Complexity |
|---|---|---|
| Random input | 17 | O(n log n) |
| Already sorted | 12 | O(n log n) |
| Reverse sorted | 12 | O(n log n) |

## Complexity Analysis

| Measure | Complexity |
|---|---|
| Best case | O(n log n) |
| Average case | O(n log n) |
| Worst case | O(n log n) |
| Space | O(n) |

The list is halved about log n times, and each level of merging does about n work, so the total is n log n in every case. Sorted and reverse sorted inputs need fewer comparisons because one half is entirely smaller than the other, so the merge finishes early and copies the remaining elements without comparing them.

## Project Structure

```
.
├── merge_sort.py
└── README.md
```
