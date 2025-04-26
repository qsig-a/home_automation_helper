from random import choice,shuffle
import time,copy

def Boggle(size):
    
    bdies4 = [["A","E","A","N","E","G"],
    ["A","H","S","P","C","O"],
    ["A","B","B","J","O","O"],
    ["A","F","F","K","P","S"],
    ["A","O","O","T","T","W"],
    ["C","I","M","O","T","U"],
    ["D","E","I","L","R","X"],
    ["D","E","L","R","V","Y"],
    ["D","I","S","T","T","Y"],
    ["E","E","G","H","N","W"],
    ["E","E","I","N","S","U"],
    ["E","H","R","T","V","W"],
    ["E","I","O","S","S","T"],
    ["E","L","R","T","T","Y"],
    ["H","I","M","N","U","T"],
    ["H","L","N","N","R","Z"]
    ]

    bdies5 = [
    ["Q","B","Z","J","X","K"],
    ["H","H","L","R","D","C"],
    ["T","E","L","P","C","I"],
    ["T","T","O","T","E","M"],
    ["A","E","A","E","E","E"],
    ["T","O","U","O","T","C"],
    ["N","H","D","T","H","C"],
    ["S","S","N","S","E","U"],
    ["S","C","T","I","E","P"],
    ["Y","I","F","P","S","R"],
    ["O","V","W","R","G","R"],
    ["L","H","N","R","O","D"],
    ["R","I","Y","P","R","H"],
    ["E","A","N","D","N","N"],
    ["E","E","E","E","M","A"],
    ["A","A","A","F","S","R"],
    ["A","F","A","I","S","R"],
    ["D","O","R","D","L","N"],
    ["M","N","N","E","A","G"],
    ["I","T","I","T","I","E"],
    ["A","U","M","E","E","G"],
    ["Y","I","F","A","S","R"],
    ["C","C","W","N","S","T"],
    ["U","O","T","O","W","N"],
    ["E","T","I","L","I","C"],
]
    begin_list4 = [2,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,29,48,0,27]
    mid_l4 = [
        [15,20,0,0,0,0,0,0,66,1,1,1,1,66,0,0,0,0,30,48,0,27],
        [7,9,0,0,0,0,0,0,66,1,1,1,1,66,0,0,0,0,31,48,0,28],
        [7,13,0,0,0,0,0,0,66,1,1,1,1,66,0,0,0,0,32,48,0,29],
        [12,5,0,0,0,0,0,0,66,1,1,1,1,66,0,0,0,0,33,48,0,31]
        ]
    end_list4 = [5,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,34,48,27,27]

    mid_l5 = [
        [2,0,0,0,0,0,0,66,1,1,1,1,1,66,0,0,0,0,29,48,0,27],
        [15,20,0,0,0,0,0,66,1,1,1,1,1,66,0,0,0,0,30,48,0,27],
        [7,9,0,0,0,0,0,66,1,1,1,1,1,66,0,0,0,0,31,48,0,28],
        [7,13,0,0,0,0,0,66,1,1,1,1,1,66,0,0,0,0,32,48,0,29],
        [12,5,0,0,0,0,0,66,1,1,1,1,1,66,0,0,0,0,33,48,0,31]
        ]
    end_list5 = [5,0,0,0,0,0,0,66,66,66,66,66,66,66,0,0,0,0,34,48,27,27]
    
    if size == "4":
        bdies = bdies4
        begin_list = begin_list4
        end_list = end_list4
        mid_l = mid_l4
    elif size == "5":
        bdies = bdies5
        end_list = end_list5
        mid_l = mid_l5

    shuffle(bdies)
    letters = []
    numbers = []
    for die in bdies:
        letters.append(choice(die))
    for letter in letters:
        letter = letter.lower()
        number = ord(letter) - 96
        numbers.append(number)
    num = choice(numbers)
    for i, x in enumerate(mid_l):
        for j,a in enumerate(x):
            if a == 1:
                num = choice(numbers)
                mid_l[i][j] = num
                numbers.remove(num)
    
    if size == "4":
        mid_l.insert(0,begin_list)
        mid_l.append(end_list)
    elif size =="5":
        mid_l.append(end_list)
    
    start = mid_l
    end = copy.deepcopy(mid_l)

    for g, h in enumerate(end):
        for v,b in enumerate(h):
            if b == 66:
                end[g][v] = 63

    return start,end