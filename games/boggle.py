from random import choice,shuffle

def Boggle4x4():

    bdies = [["A","E","A","N","E","G"],
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
    begin_list = [69,2,15,7,7,12,5,0,20,9,13,5,0,0,0,0,0,0,0,0,0,0]
    end_list = [0,0,0,0,0,0,0,0,0,0,2,15,7,7,12,5,0,20,9,13,5,69]
    mid_l = [[0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0]]
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
    mid_l.insert(0,begin_list)
    mid_l.append(end_list)
    return mid_l