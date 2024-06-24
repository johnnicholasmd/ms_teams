
// ====================================================================================
function processTicketFollowupInnerIntent(intent, ticketNumber) {
  //  console.log("Intent inside func: ", intent);
  if (isValid(textarea.value)) {
    const userMessage = textarea.value;
    //console.log(userMessage);
    var tempId = document.getElementById("temp-id").dataset.tempId;
    displaySentMessage(userMessage);
    displayTypingIndicator();
    textarea.value = "";
    textarea.rows = 1;
    textarea.focus();
    chatboxNoMessage.style.display = "none";

    fetch(`/ticket_followup/${tempId}/${ticketNumber}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ userMessage }),
    })
      .then((response) => {
        if (response.ok) {
          return response.text();
        } else {
          throw new Error("No Model found here in my JS code");
        }
      })
      .then((data) => {
        isAutoResponseDisplayed = 0;
        hideTypingIndicator();
        displayReceivedMessage(data);
        scrollBottom();
        disableRadioButtons(false);
        resetRadioButtons();
        resetInactivityTimerWithFeedback(); // Reset the idle timer after receiving AI response
      })
      .catch((error) => {
        console.error("Error:", error);
        hideTypingIndicator();
        displayReceivedMessage(
          "Sorry for the inconvenience. I am encountering an error in generating a response. Let me try again or escalate this to my support team for further assistance"
        );
        scrollBottom();
      });
  }
}// ====================================================================================

function processTicketFollowupIntent(intent) {
    //  console.log("Intent inside func: ", intent);
    if (isValid(textarea.value)) {
      const userMessage = textarea.value;
      //console.log(userMessage);
      var tempId = document.getElementById("temp-id").dataset.tempId;
      displaySentMessage(userMessage);
      displayTypingIndicator();
      textarea.value = "";
      textarea.rows = 1;
      textarea.focus();
      chatboxNoMessage.style.display = "none";
  
      fetch(`/ticket_followup/${tempId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ userMessage }),
      })
        .then((response) => {
          if (response.ok) {
            return response.text();
          } else {
            throw new Error("No Model found here in my JS code");
          }
        })
        .then((data) => {
          isAutoResponseDisplayed = 0;
          hideTypingIndicator();
          displayReceivedMessage(data);
          scrollBottom();
          disableRadioButtons(false);
          resetRadioButtons();
          resetInactivityTimerWithFeedback(); // Reset the idle timer after receiving AI response
        })
        .catch((error) => {
          console.error("Error:", error);
          hideTypingIndicator();
          displayReceivedMessage(
            "Sorry for the inconvenience. I am encountering an error in generating a response. Let me try again or escalate this to my support team for further assistance"
          );
          scrollBottom();
        });
    }
  }

// ====================================================================================
function handleTicketFollowupRequest(intent,ticketNumber) {
    const userMessageTxtArea = document.getElementById("userMessage");
    userMessageTxtArea.value = user_input;
    hideInnerButtons();
    processTicketFollowupInnerIntent(intent, ticketNumber); 
}

 // Handles the  Ticket Follow up Info Buttons Functionality
 function handleTicketFollowupBtn(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideInnerButtons();
  processTicketFollowupInnerIntent(intent, ticketNumber);
}


// ====================================================================================
function showTicketFollowupOption(intent, header) {
  disableChatboxInput();
  let aiResponseElement = "";

  if ((intent === "follow-up-flow" && header === "email_confirmation")) {
    aiResponseElement = `
      <div class="button-options" id="btnCont-options" hidden>
          <div class="btn-req">
              <button id="followupYes" onclick="handleEmailOption('Yes', '${intent}')">Yes</button>
          </div>
          <div class="btn-req">
          <button id="followupNo" onclick="handleEmailOption('No, thanks!', '${intent}')">No, thanks!</button>
          </div>
      </div> 
  `;
  }
  console.log('aiResponseElement: ', aiResponseElement);
  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}

// Processes the Options buttons
function handleEmailOption(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideEmailOptionButtons();
  processTicketFollowupIntent(intent);
  // checkFollowUpDetails(intent, ticketNumData);
}

// Hides Options Buttons
function hideEmailOptionButtons() {
  enableChatBoxInput();
  const buttonContainer = document.getElementById("btnCont-options");
  if (buttonContainer) {
    // buttonContainer.style.display = "none";
    buttonContainer.remove();
  }
}
// ====================================================================================
function showFollowupMoreInfoOption(intent, header, ticketNumber) {
  disableChatboxInput();
  let aiResponseElement = "";

  if ((intent === "follow-up-flow" && header === "more-info")) {
    aiResponseElement = `
      <div class="button-options" id="btnCont-options" hidden>
          <div class="btn-req">
              <button id="MoreinfoYes" onclick="handleFollowUpMoreInfoYes('Yes', '${intent}', 'i have questions about ${ticketNumber}')">Yes</button>
          </div>
          <div class="btn-req">
          <button id="MoreinfoNo" onclick="handleFollowUpMoreInfoNo('No', '${intent}')">No</button>
          </div>
      </div> 
  `;
  }
  console.log('aiResponseElement: ', aiResponseElement);
  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}

// Processes the Options buttons
function handleFollowUpMoreInfoYes(buttonText, intent, user_input) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideFollowUpMoreInfoButtons();
  handleTixReq(intent, user_input);;
}
// Processes the Options buttons
function handleFollowUpMoreInfoNo(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideFollowUpMoreInfoButtons();
  processTicketFollowupIntent(intent);
}


// Hides Options Buttons
function hideFollowUpMoreInfoButtons() {
  enableChatBoxInput();
  const buttonContainer = document.getElementById("btnCont-options");
  if (buttonContainer) {
    // buttonContainer.style.display = "none";
    buttonContainer.remove();
  }
} 


  

  
  