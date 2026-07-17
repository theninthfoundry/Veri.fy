# Solutions to C Programming Objective & Match Questions

This document contains the complete and verified solutions for all 53 problems (52 objective questions, 3 matching lists, and 3 file-handling programs) from the [Objetive Questions_1.pdf](file:///C:/Users/namir/Downloads/Objetive%20Questions_1.pdf) document.

---

## Part 1: Objective & Short Questions (1-52)

### 1. Structure Access
A member variable of structure is accessed by using **dot (.) operator** (or the arrow `->` operator when using a pointer).

### 2. Linked List Data Structure Type
Linked list is a **Dynamic** and **Linear** data structure.
* *Explanation:* It allocates memory dynamically at runtime and maintains sequential ordering.

### 3. Minimized Structure Size
Which minimizes size of structure? **Bit Field**.
* *Explanation:* Bit fields specify the exact bit width of members, allowing fields to pack tightly within memory bounds.

### 4. Linked List Node Fields
In linked list, second field is a **pointer (link field / address of next node)**.

### 5. Collection of Homogeneous Elements
**Array** is a collection of homogeneous (same data type) elements.

### 6. Bit Field Declaration
Bit fields can only be declared as part of a structure: **True**.

### 7. Output of Enum Program
```c
enum colour { blue, red, yellow };
enum colour c = yellow;
printf("%d", c);
```
**Output:** **2**
* *Explanation:* Unless specified, enum constants are assigned values starting from 0 (`blue = 0`, `red = 1`, `yellow = 2`).

### 8. The Pointer Member Access Operator
The `->` operator is used for **accessing structure members using a pointer**.

### 9. File Opening Failure Return Value
If there is any error while opening a file, `fopen` will return **NULL**.

### 10. Write String to File Function
Select a function which is used to write a string to a file: **fputs()** (or `fprintf()`).

### 11. Singly Linked List Node Structure
In linked list each node contains a minimum of two fields. One field is the data field to store the data. The second field is **pointer (address of next node)**.

### 12. File Mode for Both Reading and Writing
The mode which is used to open an existing file for both reading and writing is **"r+"**.

### 13. End of File Checker
What is the function `feof()` used for in C? **checking end of file (EOF)**.

### 14. Linked List Memory Allocation
Linked list is considered as an example of **Dynamic memory allocation**.

### 15. Command Line Arguments Indicator
What do `argc` and `argv` indicate? **command line arguments**.
* *Explanation:* `argc` represents the argument count, and `argv` represents the argument vector (array of strings representing parameters passed).

### 16. Read Mode in Binary
`fopen("demo.txt", "rb")` means **open file in read mode (binary mode)**.

### 17. Use of fwrite()
`fwrite()` can be used only with binary files: **No**.
* *Explanation:* `fwrite()` writes raw bytes to a file. It can be executed on both text and binary streams, though it is typically associated with binary data.

### 18. fopen() Failure Return Value
`fopen()` failure returns **NULL**.

### 19. Output of File Character Stream Program
```c
int main() {
    FILE *fp;
    char ch;
    fp = fopen("demo.txt", "r"); // demo.txt contains: "you are a good programmer"
    while((ch = fgetc(fp)) != EOF) {
        printf("%c", ch);
    }
}
```
**Output:** **you are a good programmer**

### 20. fseek() Origin Constants
In the `fseek(fp, 6, SEEK_SET)` function, the possible values for the origin offset are:
- **`SEEK_SET` (0)**: Moves pointer relative to beginning of file.
- **`SEEK_CUR` (1)**: Moves pointer relative to current position.
- **`SEEK_END` (2)**: Moves pointer relative to end of file.

### 21. fseek() Purpose
`fseek()` means **moves the file pointer to a specified position**.

### 22. ftell() Purpose
`ftell()` means **returns current position of file pointer (offset from start in bytes)**.

### 23. rewind() Purpose
`rewind` means **moves file pointer back to the beginning of the file** (equivalent to `fseek(fp, 0, SEEK_SET)` and clears errors).

### 24. Union Member Overwrite Behavior
```c
#include <stdio.h>
union Test {
    int x;
    float y;
};
int main() {
    union Test t;
    t.x = 10;
    t.y = 20.5;
    printf("%d\n", t.x);
}
```
**Output:** **Garbage value / unpredictable output**
* *Explanation:* Members of a union share the same memory location. Assigning `t.y = 20.5` overwrites the binary layout of the integer `t.x`, resulting in garbage output when interpreting the IEEE 754 float representation as an integer.

### 25. Output of Nested Structure Initialization
```c
struct Address {
    char city[20];
    int pin;
};
struct student {
    int id;
    struct Address addr;
};
int main() {
    struct student s1 = {101, {"New York", 10001}};
    printf("%d %s %d\n", s1.id, s1.addr.city, s1.addr.pin);
    return 0;
}
```
**Output:** **101 New York 10001**

### 26. Enum Assignment Calculations
```c
enum Days { SUN = 1, MON, TUE = 5, WED };
int main() {
    printf("%d %d %d %d\n", SUN, MON, TUE, WED);
    return 0;
}
```
**Output:** **1 2 5 6**
* *Explanation:* Explicit assignments modify the automatic sequence. `SUN` is set to 1, making `MON` increment to 2. `TUE` is explicitly set to 5, making `WED` increment to 6.

### 27. Bit Fields Width Limits
```c
struct Example {
    unsigned int a : 2;
    unsigned int b : 2;
};
int main() {
    struct Example e = {1, 2};
    printf("%d %d\n", e.a, e.b);
    return 0;
}
```
**Output:** **1 2**
* *Explanation:* An unsigned 2-bit field has a range of `0 to 3`. Values 1 and 2 fit correctly within bounds.

### 28. Singly Linked List Node Contents
What does a single Node in singly linked list contain? **Data field and pointer (link) field**.

### 29. Heterogeneous Variable Group
A **structure** is a collection of heterogeneous (different data types) elements.

### 30. Structure Pointer Array Math
```c
#include <stdio.h>
struct course {
    int courseno;
    char coursename[25];
};
int main() {
    struct course c[] = {{102, "Java"}, {103, "PHP"}, {104, "DotNet"}};
    printf("%d ", c[1].courseno);
    printf("%s\n", (*(c+2)).coursename);
}
```
**Output:** **103 DotNet**
* *Explanation:* `c[1].courseno` refers to the second element (`103`). `*(c+2)` dereferences the third element (`c[2]`), printing `"DotNet"`.

### 31. String Reversal Program
```c
#include <stdio.h>
#include <string.h>
int main() {
    char sentence[80];
    int i;
    printf("Enter a line of text\n");
    gets(sentence); // Reads string
    for(i = strlen(sentence) - 1; i >= 0; i--)
        putchar(sentence[i]);
    return 0;
}
```
**Output:** **Reverse of the input string**

### 32. Structure Instantiation Output
```c
#include <stdio.h>
void main() {
    struct student {
        int no;
        char name[20];
    };
    struct student s;
    s.no = 8;
    printf("%d", s.no);
}
```
**Output:** **8**

### 33. Size of Union Calculation
The size of a union is determined by the size of the **largest member**.

### 34. Sizeof Union with Array
```c
union uTemp {
    double a;      // 8 bytes
    int b[10];     // 10 * 4 = 40 bytes
    char c;        // 1 byte
} u;
```
**Output Size:** **40 bytes**
* *Explanation:* The largest member is `int b[10]` which takes `40 bytes` of memory.

### 35. Union Access Operators
Members of a union are accessed **using the dot (.) operator** (or `->` with pointers).

### 36. Structure Member Access Keyword
What is the keyword used to access a member of a structure variable in C? **dot (.) operator** (or the member selector operator).

### 37. Empty Structure Size
What is the size of an empty structure in C?
- **0 bytes** (on GCC compilers, which allow zero-sized empty structures as an extension).
- *Standard C:* Standard C does not allow empty structures. In C++, the size is **1 byte** to ensure distinct memory addresses.

### 38. Nested Unions
Can a union contain another union as a member in C? **Yes**.

### 39. Structure Pointer Access Operator
Which operator is used to access members of a structure pointer in C? **arrow (->) operator**.

### 40. Sizeof Structure
```c
struct Student {
    int rollno;     // 4 bytes
    char name[20];  // 20 bytes
};
```
**Output Size:** **24 bytes** (assuming 4-byte aligned int values).

### 41. Sizeof simple Union
```c
union Test {
    int a;    // 4 bytes
    char b;   // 1 byte
};
```
**Output Size:** **4 bytes** (matches choice **b**; size of largest member `int a`).

### 42. File Handling Standard Library
Which header file should be included in C for file manipulation operations? **<stdio.h>**.

### 43. Linked List Dereferenced Arithmetic
```c
struct node {
    int data;
    struct node* next;
};
int main() {
    struct node n1 = {10, NULL};
    struct node n2 = {20, NULL};
    n1.next = &n2;
    printf("%d", n1.data + n1.next->data);
}
```
**Output:** **30** (evaluates to `10 + 20 = 30`).

### 44. Copy-by-Value Struct Assignment
```c
#include <stdio.h>
struct info {
    int x;
};
int main() {
    struct info a = {10};
    struct info b = a; // Copy-by-value
    b.x = 20;
    printf("%d %d", a.x, b.x);
    return 0;
}
```
**Output:** **10 20**
* *Explanation:* C structs assign by value. `b = a` copies `a`'s values into a separate memory location. Thus, modifying `b.x` does not alter `a.x`.

### 45. Find File Size in Bytes
You can use **fseek() and ftell()** functions to check the size of a file in C.
* *Usage:* Seek to end: `fseek(fp, 0, SEEK_END);` then fetch position: `size = ftell(fp);`.

### 46. Union Memory Restriction
At a time, a union can store **only one member value**.

### 47. Assigning to Multiple Union Members
What happens if you assign values to multiple union members? **The last assigned value is stored correctly; previous member values are overwritten/corrupted**.

### 48. Formatted File Input/Output
Which functions write and read formatted data to files? **fprintf() and fscanf()**.

### 49. File Pointer Variable type
Which pointer is used for file handling? **FILE pointer (`FILE *`)**.

### 50. Value Copying Output
```c
struct student {
    int id;
    float marks;
};
struct student s1 = {1, 90.5};
struct student s2 = s1;
s2.marks = 80.0;
printf("%0.1f %0.1f", s1.marks, s2.marks);
```
**Output:** **90.5 80.0**

### 51. fgetc Output
```c
FILE *fp;
char ch;
fp = fopen("data.txt", "r"); // data.txt contains "Hello"
ch = fgetc(fp);
printf("%c", ch);
```
**Output:** **H**

### 52. Append Mode Behavior
```c
FILE *fp = fopen("data.txt", "a"); // data.txt contains "Hello"
fprintf(fp, "Hi");
```
**File contents after execution:** **HelloHi** (since `"a"` appends to the end).

---

## Part 2: MATCH the Following (Page 8-9)

### Match Set 1
1. **`stack`** $\rightarrow$ **c) insertion and deletion at same end**
2. **`fseek()`** $\rightarrow$ **a) move or change the position of the file pointer**
3. **`ftell()`** $\rightarrow$ **b) find out the position of the file pointer**

### Match Set 2
1. **`fgetw()`** $\rightarrow$ **b) used to read an integer from the given file**
2. **`fgetc()`** $\rightarrow$ **c) reading the character from an available file**
3. **`fscanf()`** $\rightarrow$ **a) reading the data available in a file**

### Match Set 3
1. **`fprintf()`** $\rightarrow$ **c) writing data into an available file**
2. **`fputw()`** $\rightarrow$ **a) writing an integer into an available file**
3. **`fputc()`** $\rightarrow$ **b) writing any character into the program file**

---

## Part 3: C Programming Exercises

### Exercise 1: Convert File Contents to Lowercase
*Reads from `input.txt`, converts all uppercase letters to lowercase, and saves to `output.txt`.*

```c
#include <stdio.h>
#include <ctype.h>

int main() {
    FILE *fp1, *fp2;
    char ch;

    fp1 = fopen("input.txt", "r");
    fp2 = fopen("output.txt", "w");

    if (fp1 == NULL || fp2 == NULL) {
        printf("Error: File cannot be opened\n");
        return 1;
    }

    while ((ch = fgetc(fp1)) != EOF) {
        // Convert to lowercase if uppercase
        if (ch >= 'A' && ch <= 'Z') {
            ch = ch + 32; // or tolower(ch)
        }
        fputc(ch, fp2);
    }

    printf("Success: Contents converted to lowercase and copied.\n");
    fclose(fp1);
    fclose(fp2);
    return 0;
}
```

### Exercise 2: Calculate Factorial from File
*Reads an integer from `input.txt`, computes its factorial, and writes output formatted into `output.txt`.*

```c
#include <stdio.h>

int main() {
    FILE *fp1, *fp2;
    int n, i;
    long long fact = 1;

    fp1 = fopen("input.txt", "r");
    fp2 = fopen("output.txt", "w");

    if (fp1 == NULL || fp2 == NULL) {
        printf("Error in opening files\n");
        return 1;
    }

    if (fscanf(fp1, "%d", &n) != 1) {
        printf("Error reading number from file\n");
        fclose(fp1);
        fclose(fp2);
        return 1;
    }

    for (i = 1; i <= n; i++) {
        fact = fact * i;
    }

    fprintf(fp2, "Factorial of %d is %lld", n, fact);

    fclose(fp1);
    fclose(fp2);
    return 0;
}
```

### Exercise 3: Prime Number Checker via Files
*Reads an integer from `input.txt`, checks if it is prime, and writes the decision output to `output.txt`.*

```c
#include <stdio.h>

int main() {
    FILE *fp1, *fp2;
    int n, i, count = 0;

    fp1 = fopen("input.txt", "r");
    fp2 = fopen("output.txt", "w");

    if (fp1 == NULL || fp2 == NULL) {
        printf("Error in opening files\n");
        return 1;
    }

    if (fscanf(fp1, "%d", &n) != 1) {
        printf("Error reading number from file\n");
        fclose(fp1);
        fclose(fp2);
        return 1;
    }

    if (n <= 1) {
        fprintf(fp2, "%d is not a prime number", n);
    } else {
        for (i = 1; i <= n; i++) {
            if (n % i == 0) {
                count++;
            }
        }
        if (count == 2) {
            fprintf(fp2, "%d is a prime number", n);
        } else {
            fprintf(fp2, "%d is not a prime number", n);
        }
    }

    fclose(fp1);
    fclose(fp2);
    return 0;
}
```
