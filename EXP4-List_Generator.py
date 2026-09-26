import time
import tracemalloc


N = 1_000_000


# List processing
def list_processing():
    return [x * x for x in range(N)]


# Generator processing
def generator_processing():
    for x in range(N):
        yield x * x


# -------------------------------
# LIST PROCESSING
# -------------------------------

tracemalloc.start()

start_time = time.perf_counter()

result_list = list_processing()

list_time = time.perf_counter() - start_time

current, peak_list_memory = tracemalloc.get_traced_memory()

tracemalloc.stop()


# -------------------------------
# GENERATOR PROCESSING
# -------------------------------

tracemalloc.start()

start_time = time.perf_counter()

result_generator = generator_processing()

# Consume generator
for value in result_generator:
    pass

generator_time = time.perf_counter() - start_time

current, peak_generator_memory = tracemalloc.get_traced_memory()

tracemalloc.stop()


# -------------------------------
# DISPLAY RESULTS
# -------------------------------

print("----- LIST PROCESSING -----")
print("Execution Time:",
      round(list_time, 4), "seconds")
print("Peak Memory:",
      round(peak_list_memory / (1024 * 1024), 2), "MB")


print("\n----- GENERATOR PROCESSING -----")
print("Execution Time:",
      round(generator_time, 4), "seconds")
print("Peak Memory:",
      round(peak_generator_memory / (1024 * 1024), 2), "MB")


print("\n----- COMPARISON -----")

if peak_list_memory < peak_generator_memory:
    print("List used less memory.")
else:
    print("Generator used less memory.")

print("\nNote: Execution time and memory values may vary")
print("depending on the computer.")