const request = new XMLHttpRequest();
request.open("GET", '/api/ip', false);
request.send(null);
const serverIp = JSON.parse(request.responseText).ip;
const apiSocket = io("/apisocket");
const chatSocket = io("/chat");
const urlParams = new URLSearchParams(window.location.search);

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

//Chat notifications
chatSocket.on("message", message => {
  message = JSON.parse(message);
  let allowed = !+localStorage.getItem("notifPreferences") || (localStorage.getItem("notifPreferences") == 1 && message.to != "all");
  if (!urlParams.get("advanced") && window.location.pathname != "/advanced" && window.location.pathname != "/chat" && !document.getElementById("gameChat")?.src && localStorage.getItem("pausedUntil") <= Date.now() && allowed) {
    let notifBox = document.getElementById("chatNotif");
    let notifText = document.getElementById("notifText");
    if (notifBox) { //There is already a notification onscreen
      notifText.innerHTML = `<b>${message.from}:</b> `;
      notifText.append(message.content);
      clearTimeout(notifBox.close);
    } else {
      notifBox = document.createElement("div");
      notifBox.id = "chatNotif";
      notifBox.classList.add("hCentered", "dark", "blue");
      notifText = document.createElement("div");
      notifText.id = "notifText";
      notifText.innerHTML = `<b>${message.from}:</b> `;
      notifText.append(message.content);
      notifText.onclick = () => {
        notifBox.remove();
        window.open("/chat");
      };
      notifBox.append(notifText);
      let notifButtons = document.createElement("div");
      notifButtons.id = "notifButtons";
      let pauseButton = new Image();
      pauseButton.src = "../static/img/chat/pause.png";
      pauseButton.title = "Pause for 10 minutes";
      let settingsButton = new Image();
      settingsButton.src = "../static/img/chat/settings.png";
      settingsButton.title = "Notification settings";
      let closeButton = new Image();
      closeButton.src = "../static/img/chat/close.png";
      closeButton.title = "Close";
      pauseButton.onclick = function() {
        localStorage.setItem("pausedUntil", Date.now() + 600000);
        notifText.innerText = "Notifications paused for 10 minutes.";
        notifText.onclick = null;
        this.remove();
        settingsButton.remove();
        clearTimeout(notifBox.close);
        setTimeout(() => notifBox.remove(), 3000);
      };
      settingsButton.onclick = notifSettings;
      closeButton.onclick = () => notifBox.remove();
      notifButtons.append(pauseButton, settingsButton, closeButton);
      notifBox.append(notifButtons);
      document.body.append(notifBox);
      notifBox.onmouseenter = function() {
        this.hover = true;
      }
      notifBox.onmouseleave = function() {
        this.hover = false;
      }
    }
    notifBox.close = setTimeout(() => {
      if (notifBox.hover) {
        notifBox.onmouseleave = function() {
          this.style.opacity = 0;
          setTimeout(() => notifBox.remove(), 500);
        };
      } else {
        notifBox.style.opacity = 0;
        setTimeout(() => notifBox.remove(), 500);
      }
    }, 3000);
  }
});
function notifSettings() {
  document.getElementById("chatNotif")?.remove();
  let cover = document.createElement("div");
  cover.id = "cover";
  cover.classList.add("fullScreen");
  let settingsBox = document.createElement("div");
  settingsBox.id = "alertBox";
  settingsBox.style.width = "400px";
  settingsBox.style.height = "350px";
  settingsBox.classList.add("centered", "dark", "purple");
  settingsBox.innerHTML = `
    <h3 style="margin: 0; text-align: center;">Notification preferences</h3>
    <form id="notifPreferences">
      <label style="display: block; margin: 15px 0;"><input type="radio" name="notifPreferences" value="0"> All messages</label>
      <label style="display: block; margin: 15px 0;"><input type="radio" name="notifPreferences" value="1"> Private messages only</label>
      <label style="display: block; margin: 15px 0;"><input type="radio" name="notifPreferences" value="2"> None</label>
    </form>
    <div style="margin: 15px 0;"><b>Note:</b> You won't get chat notifications while on the Advanced page.</div>
  `;
  settingsBox.style.fontSize = "16px";
  okButton = document.createElement("button");
  okButton.classList.add("hCentered");
  okButton.innerText = "OK";
  okButton.onclick = () => {
    localStorage.setItem("notifPreferences", document.getElementById("notifPreferences").notifPreferences.value);
    settingsBox.remove();
    cover.remove();
  };
  settingsBox.append(okButton);
  document.body.append(cover, settingsBox);
  document.getElementById("notifPreferences").notifPreferences.value = +localStorage.getItem("notifPreferences");
}

//If the user is on a mobile device, take them to /mobile
if (
  /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) &&
  window.location.pathname != "/mobile" &&
  !(window.location.pathname == "/login" && urlParams.get("forward") == "/mobile") &&
  !(window.location.pathname == "/chat" && urlParams.get("mobile"))
) window.location = "/mobile";
