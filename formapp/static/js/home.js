//This code is used in advanced.html, basic.html, and mobile.html

let thumbs = ["up", "wiggle", "down"];
let letters = ["a", "b", "c", "d"];
let thumbButtons = Array.from(document.querySelectorAll(".thumbButton"));
let letterButtons = Array.from(document.querySelectorAll(".letterButton"));
let chosenThumb = false;
let chosenLetter = false;
let newMessages = 0;
let permsError = "You do not have high enough permissions to do this right now.";
let bgm;
let sfx;
let segment;
let gradient;
let barpix;
let meRes;
let bgmRes;
let modeRes;
let permsRes;
let pixRes;
let studentsRes;
let removeFocus;

async function getApiData(first) {
  let apiData = await Promise.all([
    getResponse("/getme"),
    getResponse("/getbgm"),
    getResponse("/getmode"),
    getResponse("/getpermissions"),
    getResponse("/getpix"),
    getResponse("/getstudents")
  ]);
  //Save every response to a variable
  meRes = apiData[0];
  bgmRes = apiData[1];
  modeRes = apiData[2];
  permsRes = apiData[3];
  pixRes = apiData[4];
  studentsRes = apiData[5];
  //Each homepage has its own init and update functions
  if (first) init();
  else update();
}

thumbButtons.forEach((button, i) => {
  button.addEventListener("keydown", event => {
    if (event.code == "Enter") thumbsVote(i);
  });
});

letterButtons.forEach((button, i) => {
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

thumbButtons.concat(letterButtons).forEach(el => {
  el.onfocus = () => {
    clearTimeout(removeFocus);
    //Remove focus from the button after 1 second so votes can be updated again
    removeFocus = setTimeout(() => document.activeElement.blur(), 1000);
  }
});


function thumbsVote(thumb) {
  if (chosenThumb === thumb) {
    chosenThumb = false;
    removeHighlight("thumbButton" + thumb);
    request.open("GET", "/tutd?thumb=oops");
  } else {
    chosenThumb = thumb;
    request.open("GET", "/tutd?thumb=" + thumbs[thumb]);
    //Highlight selected button and reset others
    thumbButtons.forEach((button, i) => {
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
    letterButtons.forEach((button, i) => {
      i == letter ? highlight("letterButton" + letter) : removeHighlight("letterButton" + i);
    });
  }
  request.send();
}

function updateVotes() {
  //Make sure a thumb/letter button is not currently active (to prevent immediately reverting a vote)
  if (!thumbButtons.includes(document.activeElement) && !letterButtons.includes(document.activeElement)) {
    //Make sure displayed vote matches actual vote, for example if new poll is started or page is reloaded
    let thumb = meRes.thumb ? thumbs.indexOf(meRes.thumb) : false;
    let letter = meRes.letter ? letters.indexOf(meRes.letter) : false;
    if (thumb === false && chosenThumb !== false) thumbsVote(chosenThumb); //Remove the vote
    else if (thumb !== chosenThumb) thumbsVote(thumb);
    if (letter === false && chosenLetter !== false) thumbsVote(chosenLetter); //Remove the vote
    else if (letter !== chosenLetter) letterVote(letter);
  }

  let textResEl = document.getElementById("response");
  let response = meRes.textRes;
  if (response && !textResEl.value) {
    textResEl.value = response;
    checkResponse();
    responseSubmitted();
  }
  if (!response && textResEl.value) responseUnsubmitted();
}

function highlight(image) {
  let button = document.getElementById(image);
  button.src = button.src.replace(".png", "-highlight.png");
  button.classList.add("highlight");
  button.title = "Remove";
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

function checkResponse() {
  let box = document.getElementById("response");
  let button = document.getElementById("submitResponse");
  if (box.value) {
    button.classList.remove("unselectable");
    button.onclick = submitResponse;
  } else {
    button.classList.add("unselectable");
    button.onclick = null;
  }
}

function submitResponse() {
  let box = document.getElementById("response");
  request.open("POST", "/textresponse?response=" + box.value);
  request.send();
  responseSubmitted();
}

function responseSubmitted() {
  let box = document.getElementById("response");
  let button = document.getElementById("submitResponse");
  box.disabled = true;
  box.classList.add("unselectable");
  button.innerText = "Unsubmit";
  button.onclick = unsubmitResponse;
}

function unsubmitResponse() {
  let box = document.getElementById("response");
  request.open("GET", "/textresponse?response=");
  request.send();
  responseUnsubmitted();
}

function responseUnsubmitted() {
  let box = document.getElementById("response");
  let button = document.getElementById("submitResponse");
  box.disabled = false;
  box.classList.remove("unselectable");
  button.innerText = "Submit";
  button.onclick = submitResponse;
}

function shorten(container, maxHeight, text, maxWidth) {
  //Set title to original string
  let original = text.innerText;
  //Remove characters while string is too long
  while (container.clientHeight > maxHeight || container.clientWidth > maxWidth) text.innerText = text.innerText.substring(0, text.innerText.length - 2) + "…";
  text.title = original;
  text.style.cursor = "help";
}

function ticketsText() {
  let users = Object.values(studentsRes);
  let helpTickets = users.filter(user => user.help);
  let breakRequests = users.filter(user => user.breakReq);
  let el = document.getElementById("ticketsText");
  let helpText = helpTickets.length == 1 ? "There is currently 1 help ticket in." : `There are currently ${helpTickets.length} tickets in.`
  let breakText = breakRequests.length == 1 ? "1 student has requested a bathroom break." : `${breakRequests.length} students have requested bathroom breaks.`;
  el.innerHTML = helpText + "<br>" + breakText;
}

function usersText() {
  let users = Object.values(studentsRes);
  let students = users.filter(user => user.perms == permsRes.student);
  let el = document.getElementById("usersText");
  el.innerText = users.length == 1 ? "You are the only one logged in right now." : `${users.length} people are logged in, including ${students.length} students.`;
}

function checkForHelpTicket() {
  if (meRes.help) {
    ticketSent("help");
  } else if (meRes.breakReq) {
    ticketSent("break");
  } else {
    document.getElementById("help").onclick = requestHelp;
    document.getElementById("break").onclick = requestBreak;
  }
}

function ticketSent(type) {
  let sentEl;
  let otherEl;
  if (type == "help") {
    sentEl = document.getElementById("help");
    otherEl = document.getElementById("break");
  } else if (type == "break") {
    sentEl = document.getElementById("break");
    otherEl = document.getElementById("help");
  }
  sentEl.onclick = null;
  otherEl.onclick = null;
  sentEl.classList.add("pressed");
  sentEl.classList.add("unselectable");
  sentEl.innerText = "Ticket sent";
  otherEl.classList.add("unselectable");
}

function requestHelp() {
  let el = document.getElementById("help");
  request.open("GET", "/help?action=send");
  request.send();
  ticketSent("help");
}

function requestBreak() {
  let el = document.getElementById("break");
  request.open("GET", "/break?action=request");
  request.send();
  ticketSent("break");
}
