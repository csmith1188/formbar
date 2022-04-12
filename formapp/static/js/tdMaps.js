//The game area is a 32 x 15 square grid
//In general, maps should start and end a half-square outside this area
//Avoid the tower icons at the bottom, the buttons at the top-left, and the info at the top-right
//New maps must be added to the end of the list

//Map object template:
/*{
  name: Map name,
  author: Your name,
  start: [column, row],
  lines: [
    [direction, length],
    [direction, length],
    …
  ]
}*/

let maps = [
  {
    start: [6.5, -0.5],
    lines: [
      ["down", 13],
      ["left", 3],
      ["up", 3],
      ["right", 7],
      ["down", 2],
      ["right", 2],
      ["up", 6],
      ["left", 3],
      ["up", 3],
      ["right", 7],
      ["down", 8],
      ["right", 6],
      ["down", 3],
      ["left", 3],
      ["up", 8],
      ["right", 9],
      ["down", 4],
      ["left", 4],
      ["down", 2],
      ["right", 8]
    ]
  },
  {
    start: [-0.5, 12.5],
    lines: [
      ["right", 9],
      ["up", 10],
      ["right", 13],
      ["down", 8],
      ["left", 2],
      ["up", 6],
      ["left", 9],
      ["down", 8],
      ["right", 2],
      ["up", 6],
      ["right", 5],
      ["down", 6],
      ["right", 6],
      ["up", 10],
      ["right", 9]
    ]
  },
  {
    start: [23.5, -0.5],
    lines: [
      ["down", 3],
      ["right", 5],
      ["down", 4],
      ["left", 4],
      ["down", 3],
      ["right", 2],
      ["down", 4],
      ["left", 9],
      ["up", 4],
      ["right", 2],
      ["down", 2],
      ["left", 8],
      ["down", 1],
      ["left", 7],
      ["up", 5],
      ["right", 9],
      ["up", 5],
      ["left", 4],
      ["down", 2],
      ["right", 8],
      ["up", 1],
      ["right", 1],
      ["up", 1],
      ["right", 1],
      ["up", 1],
      ["right", 1],
      ["up", 2]
    ]
  },
  {
    start: [8.5, -0.5],
    lines: [
      ["down", 13],
      ["right", 6],
      ["up", 5],
      ["right", 4],
      ["down", 4],
      ["left", 9],
      ["up", 6],
      ["right", 7],
      ["down", 4],
      ["right", 9],
      ["down", 3],
      ["left", 5],
      ["up", 7],
      ["right", 2],
      ["down", 2],
      ["right", 4],
      ["up", 3],
      ["left", 9],
      ["up", 1],
      ["right", 4],
      ["up", 1],
      ["left", 22]
    ]
  },
  {
    start: [32.5, 7.5],
    lines: [
      ["left", 4],
      ["down", 2],
      ["left", 4],
      ["up", 2],
      ["left", 3],
      ["up", 5],
      ["left", 4],
      ["down", 5],
      ["left", 3],
      ["down", 5],
      ["left", 4],
      ["up", 5],
      ["left", 3],
      ["up", 2],
      ["left", 4],
      ["down", 2],
      ["left", 4]
    ]
  },

  //^ New maps go here ^
];
