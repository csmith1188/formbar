//This code is used in both index.html and basic.html

let thumbs = ["up", "wiggle", "down"];
let letters = ["a", "b", "c", "d"];
let thumbButtons = document.querySelectorAll(".thumbButton");
let letterButtons = document.querySelectorAll(".letterButton");
let chosenThumb = false;
let chosenLetter = false;
let meRes;
let bgmRes;
let modeRes;
let permsRes;
let pixRes;

async function getApiData(first) {
  let apiData = await Promise.all([
    getResponse("/getme"),
    getResponse("/getbgm"),
    getResponse("/getmode"),
    getResponse("/getpermissions"),
    getResponse("/getpix")
  ]);
  meRes = apiData[0];
  bgmRes = apiData[1];
  modeRes = apiData[2];
  permsRes = apiData[3];
  pixRes = apiData[4];
  if (first) init();
  else update();
}

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

function checkIfRemoved() {
  //If the user is removed by the teacher, send them back to the login page
  if (meRes.error == "You are not logged in.") window.location = "/login?alert=You have been logged out.";
}

function thumbsVote(thumb) {
  if (chosenThumb === thumb) {
    chosenThumb = false;
    removeHighlight("thumbButton" + thumb);
    request.open("GET", "/tutd?thumb=oops");
  } else {
    chosenThumb = thumb;
    request.open("GET", "/tutd?thumb=" + thumbs[thumb]);
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
    request.open("GET", "/tutd?thumb=" + letters[letter]);
    //Highlight selected button and reset others
    Array.from(letterButtons).forEach((button, i) => {
      i == letter ? highlight("letterButton" + letter) : removeHighlight("letterButton" + i);
    });
  }
  request.send();
}

function updateVotes() {
  //Make sure displayed vote matches actual vote, for example if new poll is started or user reloads
  let thumb;
  let thumb = meRes.thumb ? thumbs.indexOf(meRes.thumb) : false;
  let letter = meRes.letter ? letters.indexOf(meRes.letter) : false;
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
  switch (image) {
    case "thumbButton0":
      button.title = "Up";
      break;
    case "thumbButton1":
      button.title = "Wiggle";
      break;
    case "thumbButton2":
      button.title = "Down";
      break;
    case "letterButton0":
      button.title = "Vote A";
      break;
    case "letterButton1":
      button.title = "Vote B";
      break;
    case "letterButton2":
      button.title = "Vote C";
      break;
    case "letterButton3":
      button.title = "Vote D";
      break;
  }
}
