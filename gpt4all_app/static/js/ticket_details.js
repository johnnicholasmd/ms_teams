// ====================================================================================
function processTicketdetailsInnerIntent(intent) {
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
  
      fetch(`/check_ticket_number/${tempId}/`, {
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

  function processTicketdetailsIntent(intent) {
    //  console.log("Intent inside func: ", intent);
    if (isValid(textarea.value)) {
      const userMessage = textarea.value;
      //console.log(userMessage);
      var tempId = document.getElementById("temp-id").dataset.tempId;
      //displaySentMessage(userMessage);
      displayTypingIndicator();
      textarea.value = "";
      textarea.rows = 1;
      textarea.focus();
      chatboxNoMessage.style.display = "none";
  
      fetch(`/check_ticket_number/${tempId}/`, {
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
  
  function checkTicketDetails(intent,ticketNumber) {
    console.log("Intent inside func: ", intent);
    console.log("ticketNumber: ", ticketNumber);
    if (isValid(textarea.value)) {
      const userMessage = textarea.value;
      var tempId = document.getElementById("temp-id").dataset.tempId;
      displaySentMessage(userMessage);
      displayTypingIndicator();
      textarea.value = "";
      textarea.rows = 1;
      textarea.focus();
      chatboxNoMessage.style.display = "none";
  
      fetch(`/ticket_details/${tempId}/${ticketNumber}/`, {
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
  
  // ====================================================================================
  // [COE Purpose Functions]
  // Show buttons for COE Request Purpose

  
  // Processes the Purposes buttons
  function handlePurpose(buttonText, intent) {
    const userMessageTxtArea = document.getElementById("userMessage");
    userMessageTxtArea.value = buttonText;
    // console.log("inner button: ", intent);
    hidePurposeButtons();
    processTicketdetailsInnerIntent(intent);
  }
  
  // Hides Purposes Buttons
  function hidePurposeButtons() {
    enableChatBoxInput();
    const buttonContainer = document.getElementById("btnCont-purpose"); 
    if (buttonContainer) {
      buttonContainer.style.display = "none";
    }
  }
  // ====================================================================================
  
  // ====================================================================================
  // Handles the COE Request or Info Buttons Functionality
  function handleTixReq(intent,user_input) {
    const userMessageTxtArea = document.getElementById("userMessage");
    userMessageTxtArea.value = user_input;
    //console.log(userMessageTxtArea.value );
    hideInnerButtons();
    processTicketdetailsIntent(intent);
  }
  // Handles the  Ticket Details Request or Info Buttons Functionality
function handleTicketDetailsRequest(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideInnerButtons();
  processTicketdetailsIntent(intent);
}


  function handleTixInfo(buttonText) {
    const userMessageTxtArea = document.getElementById("userMessage");
    userMessageTxtArea.value = buttonText;
    intentData = "";
    hideInnerButtons();
    processQandA();
  }
  
  
// ====================================================================================
function showTicketDetailsOption(intent, header, ticketNumber) {
  disableChatboxInput();
  let aiResponseElement = "";

  if ((intent === "ticketdetailsflow" && header === "email_confirmation")) {
    aiResponseElement = `
      <div class="button-options" id="btnCont-options" hidden>
          <div class="btn-req">
              <button id="TicketdetailsYes" onclick="handleTicketDetailsEmailOptionYes('Yes', '${intent}', '${ticketNumber}')">Yes</button>
          </div>
          <div class="btn-req">
          <button id="TicketdetailsNo" onclick="handleTicketDetailsEmailOptionNo('No, I need other details', '${intent}', 'i have questions about ${ticketNumber}' )">No, I need other details</button>
          </div>
      </div> 
  `;
  }
  console.log('aiResponseElement: ', aiResponseElement);
  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}

// Processes the Options buttons
function handleTicketDetailsEmailOptionYes(buttonText, intent, ticketNumber) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;

  console.log("Ticket Number:", ticketNumber);


  hideTicketDetailsEmailOptionButtons();
  processTicketFollowupInnerIntent(intent, ticketNumber);
}
// Processes the Options buttons
function handleTicketDetailsEmailOptionNo(buttonText, intent, user_input) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideTicketDetailsEmailOptionButtons();
  handleTixReq(intent, user_input);
}


// Hides Options Buttons
function hideTicketDetailsEmailOptionButtons() {
  enableChatBoxInput();
  const buttonContainer = document.getElementById("btnCont-options");
  if (buttonContainer) {
    // buttonContainer.style.display = "none";
    buttonContainer.remove();
  }
} 

// =====================================================

  
  