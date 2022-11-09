const request = new XMLHttpRequest();
request.open("GET", '/api/ip', false);
request.send(null);
const serverIp = JSON.parse(request.responseText).ip;
const apiSocket = io("/apisocket");
const chatSocket = io("/chat");

chatSocket.on("disconnect", message => {
  console.log("DISCONNECTED:", message);
  //if (message == "transport error") {
  //formbarAlert("Session ended.", "alert", () => window.location.reload());
  //}
});

function getResponse(endpoint, parse = true) {
  return new Promise((resolve, reject) => {
    let newRequest = new XMLHttpRequest();
    endpoint += (endpoint.includes("?") ? "&" : "?");
    endpoint += "return=json";
    newRequest.open("GET", endpoint);
    newRequest.onload = () => {
      if (parse) {
        try {
          resolve(JSON.parse(newRequest.responseText));
        } catch {
          resolve({});
        }
      } else {
        resolve(newRequest.responseText);
      }
    };
    newRequest.send(null);
  });
}

function formbarAlert(message, type = "alert", callback, inputType = "text", promptDefault = "", width = 500, height = 300) {
  //There are three alert types: alert, confirm, and prompt.
  //For confirm and prompt, the result is passed to the callback function as an argument.
  //Example alert: formbarAlert("Type something", "prompt", input => console.log(input));

  //If there is already an alert, hide it
  document.getElementById("alertBox")?.remove();
  document.getElementById("cover")?.remove();
  let cover = document.createElement("div");
  cover.id = "cover";
  cover.classList.add("fullScreen");
  document.body.append(cover);
  let alertBox = document.createElement("div");
  alertBox.id = "alertBox";
  alertBox.style.width = width + "px";
  alertBox.style.height = height + "px";
  alertBox.classList.add("centered", "dark", "purple");
  let alertText = document.createElement("div");
  alertText.id = "alertText";
  alertText.innerHTML = message;
  alertBox.append(alertText);
  let okButton;
  let yesButton;
  let noButton;
  document.body.append(alertBox);
  if (type == "alert") {
    okButton = document.createElement("button");
    okButton.classList.add("hCentered");
    okButton.innerText = "OK";
    okButton.onclick = () => {
      alertBox.remove();
      cover.remove();
      if (callback) callback();
    };
    alertBox.append(okButton);
    okButton.focus();
  } else if (type == "confirm") {
    yesButton = document.createElement("button");
    yesButton.id = "yesButton";
    yesButton.innerText = "Yes";
    yesButton.onclick = () => {
      alertBox.remove();
      cover.remove();
      if (callback) callback(true);
    };
    alertBox.append(yesButton);
    noButton = document.createElement("button");
    noButton.id = "noButton";
    noButton.innerText = "No";
    noButton.onclick = () => {
      alertBox.remove();
      cover.remove();
      if (callback) callback(false);
    }
    alertBox.append(noButton);
    yesButton.focus();
  } else if (type == "prompt") {
    alertText.classList.add("prompt");
    let promptInput = document.createElement("input");
    promptInput.classList.add("box", "hCentered");
    promptInput.type = inputType;
    promptInput.value = promptDefault;
    alertBox.append(promptInput);
    okButton = document.createElement("button");
    okButton.classList.add("hCentered");
    okButton.innerText = promptDefault ? "OK" : "Cancel";
    promptInput.oninput = function() {
      if (this.value) okButton.innerText = "OK";
      else okButton.innerText = "Cancel";
    }
    okButton.onclick = () => {
      alertBox.remove();
      cover.remove();
      if (callback) callback(promptInput.value);
    };
    promptInput.addEventListener("keydown", e => {
      if (e.key == "Enter") okButton.click();
    });
    alertBox.append(okButton);
    promptInput.focus();
  }
}

const urlParams = new URLSearchParams(window.location.search);

//If the user is on a mobile device, take them to /mobile
if (
  /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) &&
  window.location.pathname != "/mobile" &&
  !(window.location.pathname == "/login" && urlParams.get("forward") == "/mobile") &&
  !(window.location.pathname == "/chat" && urlParams.get("mobile"))
) window.location = "/mobile";
