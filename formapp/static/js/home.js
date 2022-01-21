//This code is used in both index.html and basic.html

let thumbButtons = document.querySelectorAll(".thumbButton");
let letterButtons = document.querySelectorAll(".letterButton");
let chosenThumb = false;
let chosenLetter = false;
let meRes = getResponse("/getme");
let bgmRes = getResponse("/getbgm");
let modeRes = getResponse("/getmode");
let permsRes = getResponse("/getpermissions");
let pixRes = getResponse("/getpix");


updateVotes(meRes);
setInterval(() => {
  meRes = getResponse("/getme");
  ////bgmRes = getResponse("/getbgm");
  ////modeRes = getResponse("/getmode");
  ////permsRes = getResponse("/getpermissions");
  checkIfRemoved(meRes);
  updateVotes(meRes);
}, 1000);

Array.from(thumbButtons).forEach((button, i) => {
  button.addEventListener("keydown", event => {
    if (event.code == "Enter") thumbsVote(i);
  });
});

Array.from(letterButtons).forEach((button, i) => {
  button.addEventListener("keydown", event => {
    if (event.code == "Enter") {
      letterVote(i);
    }
  });
});

function checkIfRemoved(res) {
  //If the user is removed by the teacher, send them back to the login page
  if (res.error == "You are not logged in.") window.location = "/login?alert=You have been logged out.";
}

function thumbsVote(thumb) {
  if (chosenThumb === thumb) {
    chosenThumb = false;
    removeHighlight("thumbButton" + thumb);
    request.open("GET", "/tutd?thumb=oops");
  } else {
    chosenThumb = thumb;
    if (thumb == 0) {
      request.open("GET", "/tutd?thumb=up");
    } else if (thumb == 1) {
      request.open("GET", "/tutd?thumb=wiggle");
    } else if (thumb == 2) {
      request.open("GET", "/tutd?thumb=down");
    }
    //Highlight selected button and reset others
    Array.from(thumbButtons).forEach((button, i) => {
      i == thumb ? highlight("thumbButton" + thumb) : removeHighlight("thumbButton" + i);
    });
  }
  request.send();
}

function letterVote(letter) {
  if (chosenLetter === letter) {
    chosenLetter = false;
    removeHighlight("letterButton" + letter);
    request.open("GET", "/abcd?vote=oops");
  } else {
    chosenLetter = letter;
    if (letter == 0) {
      request.open("GET", "/abcd?vote=a");
    } else if (letter == 1) {
      request.open("GET", "/abcd?vote=b");
    } else if (letter == 2) {
      request.open("GET", "/abcd?vote=c");
    } else if (letter == 3) {
      request.open("GET", "/abcd?vote=d");
    }
    //Highlight selected button and reset others
    Array.from(letterButtons).forEach((button, i) => {
      i == letter ? highlight("letterButton" + letter) : removeHighlight("letterButton" + i);
    });
  }
  request.send();
}

function updateVotes(res) {
  //Make sure displayed vote matches actual vote, for example if new poll is started or user reloads
  let thumb;
  if (res.thumb == "up") thumb = 0;
  else if (res.thumb == "wiggle") thumb = 1;
  else if (res.thumb == "down") thumb = 2;
  else thumb = false;
  let letter;
  if (res.letter == "a") letter = 0;
  else if (res.letter == "b") letter = 1;
  else if (res.letter == "c") letter = 2;
  else if (res.letter == "d") letter = 3;
  else letter = false;
  if (thumb === false && chosenThumb !== false) thumbsVote(chosenThumb); //Remove the vote
  else if (thumb !== chosenThumb) thumbsVote(thumb);
  if (letter === false && chosenLetter !== false) thumbsVote(chosenLetter); //Remove the vote
  else if (letter !== chosenLetter) letterVote(letter);
}

function highlight(image) {
  let button = document.getElementById(image);
  button.src = button.src.replace(".png", "-highlight.png");
  button.classList.add("highlight");
  button.title = "Cancel";
}

function removeHighlight(image) {
  let button = document.getElementById(image);
  button.src = button.src.replace("-highlight", "");
  button.classList.remove("highlight");
  if (image == "thumbButton0") button.title = "Up";
  if (image == "thumbButton1") button.title = "Wiggle";
  if (image == "thumbButton2") button.title = "Down";
  if (image == "letterButton0") button.title = "Vote A";
  if (image == "letterButton1") button.title = "Vote B";
  if (image == "letterButton2") button.title = "Vote C";
  if (image == "letterButton3") button.title = "Vote D";
}
