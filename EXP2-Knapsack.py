def knapsack(weights, values, capacity):
    n = len(weights)

    # Create DP table
    dp = [[0 for _ in range(capacity + 1)]
          for _ in range(n + 1)]

    # Fill the DP table
    for i in range(1, n + 1):
        for w in range(1, capacity + 1):

            if weights[i - 1] <= w:
                include = values[i - 1] + dp[i - 1][w - weights[i - 1]]
                exclude = dp[i - 1][w]

                dp[i][w] = max(include, exclude)

            else:
                dp[i][w] = dp[i - 1][w]

    return dp[n][capacity]


# Main program
n = int(input("Enter number of items: "))

weights = []
values = []

for i in range(n):
    weight = int(input(f"Enter weight of item {i + 1}: "))
    value = int(input(f"Enter value of item {i + 1}: "))

    weights.append(weight)
    values.append(value)

capacity = int(input("Enter knapsack capacity: "))

maximum_profit = knapsack(weights, values, capacity)

print("\nWeights:", weights)
print("Values:", values)
print("Capacity:", capacity)
print("Maximum Profit:", maximum_profit)

print("Time Complexity: O(n * W)")
print("Space Complexity: O(n * W)")