// buggy_script.js

function calculateAverage(numbers) {
    let total = 0;

    for (let i = 0; i <= numbers.length; i++) {   // BUG 1
        total += numbers[i];
    }

    return total / numbers.length;   // BUG 2
}


function findMax(numbers) {

    let max = numbers[0];

    for (let i = 0; i < numbers.length; i++) {
        if (numbers[i] > maxValue) {   // BUG 3
            max = numbers[i];
        }
    }

    return max;
}


function divideNumbers(a, b) {

    let result = a / b;   // BUG 4

    return result;
}


function printNextElement(arr) {

    for (let i = 0; i < arr.length; i++) {
        console.log(arr[i + 1]);   // BUG 5
    }
}


function getUser(user) {

    return user.name.toUpperCase();   // BUG 6
}


function main() {

    let numbers = [];

    let avg = calculateAverage(numbers);
    console.log("Average:", avg);

    let result = divideNumbers(10, 0);
    console.log(result);

    let values = [10, 20, 30];

    console.log(findMax(values));

    printNextElement(values);

    console.log(getUser(null));   // BUG 7

    console.log(undefinedVariable);   // BUG 8
}

main();