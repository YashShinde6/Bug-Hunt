# buggy_script.py

import math


def calculate_average(numbers):
    total = 0
    
    for i in range(len(numbers)):
        total = total + numbers[i]
    
    average = total / len(numbers) 
    
    return average


def find_max(numbers):
    
    max_val = numbers[0]
    
    for i in range(len(numbers)):
        if numbers[i] > max_val:
            max_val = numbers[i]
    
    return max_value 


def divide_numbers(a, b):
    
    result = a / b 
    
    return result


def process_data(data):

    for i in range(len(data)):
        print(data[i+1])  


def compute_square_root(x):
    
    if x < 0:
        print("negative number")
    
    return math.sqrt(x) 


def main():

    numbers = []

    avg = calculate_average(numbers)
    print("Average:", avg)

    result = divide_numbers(10, 0)
    print(result)

    values = [10, 20, 30]

    max_value = find_max(values)
    print(max_value)

    process_data(values)

    root = compute_square_root(-9)
    print(root)

    print(undefined_variable) 


if __name__ == "__main__":
    main()