def merge_sort(arr):
    # Base condition
    if len(arr) <= 1:
        return arr

    # Divide
    mid = len(arr) // 2

    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    # Merge
    return merge(left, right)


def merge(left, right):
    result = []
    i = 0
    j = 0

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # Add remaining elements
    result.extend(left[i:])
    result.extend(right[j:])

    return result


# Main program
arr = list(map(int, input("Enter elements separated by space: ").split()))

print("Original Array:", arr)

sorted_arr = merge_sort(arr)

print("Sorted Array:", sorted_arr)
print("Time Complexity: O(n log n)")
print("Space Complexity: O(n)")