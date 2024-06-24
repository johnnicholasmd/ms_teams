// ====================================================================================
// For Create Ticket Innerintent only
function processCreateTicketIntent(intent) {
  //  console.log("Intent inside func: ", intent);
  if (isValid(textarea.value)) {
    const userMessage = textarea.value;
    var tempId = document.getElementById("temp-id").dataset.tempId;
    displaySentMessage(userMessage);
    displayTypingIndicator();
    textarea.value = "";
    textarea.rows = 1;
    textarea.focus();
    chatboxNoMessage.style.display = "none";

    fetch(`/create_ticket/${tempId}/`, {
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

// function processTicketDetails(intent,ticketNumber) {
//   console.log("Intent inside func: ", intent);
//   if (isValid(textarea.value)) {
//     const userMessage = textarea.value;
//     var tempId = document.getElementById("temp-id").dataset.tempId;
//     displaySentMessage(userMessage);
//     displayTypingIndicator();
//     textarea.value = "";
//     textarea.rows = 1;
//     textarea.focus();
//     chatboxNoMessage.style.display = "none";

//     fetch(`/ticket_details/${tempId}/${ticketNumber}/`, {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//         // "X-CSRFToken": csrfToken,
//       },
//       body: JSON.stringify({ userMessage }),
//     })
//       .then((response) => {
//         if (response.ok) {
//           return response.text();
//         } else {
//           throw new Error("No Model found here in my JS code");
//         }
//       })
//       .then((data) => {
//         isAutoResponseDisplayed = 0;
//         hideTypingIndicator();
//         displayReceivedMessage(data);
//         scrollBottom();
//         disableRadioButtons(false);
//         resetRadioButtons();
//         resetInactivityTimerWithFeedback(); // Reset the idle timer after receiving AI response
//       })
//       .catch((error) => {
//         console.error("Error:", error);
//         hideTypingIndicator();
//         displayReceivedMessage(
//           "Sorry for the inconvenience. I am encountering an error in generating a response. Let me try again or escalate this to my support team for further assistance"
//         );
//         scrollBottom();
//       });
//   }
// }


// ====================================================================================
// Handles the Create Ticket Request or Info Buttons Functionality
function handleCreateTicketRequest(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideInnerButtons();
  processCreateTicketIntent(intent);
}
// ====================================================================================
// For Yes/Modify/No Buttons
// Shows the 3 Option Buttons
function showCreateTicketOption(intent, index) {
  // console.log('Index: ', index);
  disableChatboxInput();
  let aiResponseElement = "";

  if ((intent === "create_ticket_flow" && index === 5) || indexData === 4) {
    aiResponseElement = `
      <div class="button-options" id="btnCont-options" hidden>
          <div class="btn-yes">
              <button id="coeYesBtn" onclick="handleOption('Yes', '${intent}')">Yes</button>
          </div>
          <div class="btn-modify">
              <button id="coeModBtn" onclick="handleOption('Modify', '${intent}')">Modify</button>
          </div>
          <div class="btn-no">
          <button id="coeNoBtn" onclick="handleOption('No', '${intent}')">No</button>
          </div>
      </div> 
  `;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}

// Processes the Purposes buttons
function handleOption(buttonText, intent) {
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = buttonText;
  // console.log("inner button: ", intent);
  hideOptionButtons();
  processCreateTicketIntent(intent);
}

// Hides Purposes Buttons
function hideOptionButtons() {
  enableChatBoxInput();
  const buttonContainer = document.getElementById("btnCont-options");
  if (buttonContainer) {
    // buttonContainer.style.display = "none";
    buttonContainer.remove();
  }
}
// ====================================================================================
function showConfirmation(intent, header) {
  disableChatboxInput();
  let aiResponseElement = "";

  if (header === "confirmation"){
    aiResponseElement = `
    <div class="button-options" id="btnCont-options" hidden>
      <div class="btn-req">
          <button id="btnYes" onclick="processConfirmation('Yes', '${intent}')">Yes</button>
      </div>
      <div class="btn-req">
      <button id="btnNo" onclick="processConfirmation('No', '${intent}')">No</button>
      </div>
</div> 
`;
  }
  console.log('aiResponseElement: ', aiResponseElement);
  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideConfirmationSelect(){
  enableChatBoxInput();
  const selectConfirmation = document.getElementById('btnCont-options');
  if (selectConfirmation){
    selectConfirmation.remove();
  }
}

function processConfirmation(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideConfirmationSelect();
  processCreateTicketIntent(intent);
}

// ====================================================================================
function showOpenedBy(header,choices,intent) {
  disableChatboxInput();
  console.log('Preparsing: ', choices);
  let aiResponseElement = "";
  let parsedChoices = JSON.parse(choices);
  console.log('Postparsing: ', parsedChoices);
  let keys = Object.keys(parsedChoices);

  let dropDownOptions = "";
  keys.forEach(key => {
    dropDownOptions += `<option value="${key}">${key}</option>`;
  });

  if (header === "openedby"){
    aiResponseElement = `
    <div class="cont-openedBy" id="btnCont-openedBy" hidden>
        <select id ="openedByDropDown" onchange="processOpenedBy(this.value, '${intent}')">
          <option disabled hidden selected> Select Person to Open </option>
          ${dropDownOptions}
        </select>
    </div> 
`;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideOpenedBySelect(){
  enableChatBoxInput();
  const selectOpenedBy = document.getElementById('btnCont-openedBy');
  if (selectOpenedBy){
    // selectOpenedBy.style.display = "none";
    selectOpenedBy.remove();
  }
}

function processOpenedBy(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideOpenedBySelect();
  processCreateTicketIntent(intent);
}
// ====================================================================================
function showUrgency(header,choices,intent) {
  disableChatboxInput()
  let aiResponseElement = "";
  let parsedChoices = JSON.parse(choices);
  let keys = Object.keys(parsedChoices);

  let dropDownOptions = "";
  keys.forEach(key => {
    dropDownOptions += `<option value="${key}">${key}</option>`;
  });

  if (header === "urgency"){
    aiResponseElement = `
    <div class="cont-urgency" id="btnCont-urgency" hidden>
        <select id ="urgencyDropDown" onchange="processUrgency(this.value, '${intent}')">
          <option disabled hidden selected> Select Urgency </option>
          ${dropDownOptions}
        </select>
    </div> 
`;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideUrgencySelect(){
  enableChatBoxInput();
  const selectUrgency = document.getElementById('btnCont-urgency');
  if (selectUrgency){
    // selectUrgency.style.display = "none";
    selectUrgency.remove();
  }
}

function processUrgency(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideUrgencySelect();
  processCreateTicketIntent(intent);
}
// ====================================================================================
function showImpact(header,choices,intent) {
  disableChatboxInput()
  let aiResponseElement = "";
  let parsedChoices = JSON.parse(choices);
  let keys = Object.keys(parsedChoices);

  let dropDownOptions = "";
  keys.forEach(key => {
    dropDownOptions += `<option value="${key}">${key}</option>`;
  });

  if (header === "impact"){
    aiResponseElement = `
    <div class="cont-impact" id="btnCont-impact" hidden>
        <select id ="impactDropdown" onchange="processImpact(this.value, '${intent}')">
          <option disabled hidden selected> Select Impact </option>
          ${dropDownOptions}
        </select>
    </div> 
`;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideImpactSelect(){
  enableChatBoxInput();
  const selectImpact = document.getElementById('btnCont-impact');
  if (selectImpact){
    // selectImpact.style.display = "none";
    selectImpact.remove();
  }
}

function processImpact(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideImpactSelect();
  processCreateTicketIntent(intent);
}

// ====================================================================================
function showCategory(header,category,intent) {
  disableChatboxInput()
  let aiResponseElement = "";
  let parsedCategory = JSON.parse(category);
  let keys = Object.keys(parsedCategory);

  let dropDownOptions = "";
  keys.forEach(key => {
    dropDownOptions += `<option value="${key}">${key}</option>`;
  });

  if (header === "category"){
    aiResponseElement = `
    <div class="cont-category" id="btnCont-category" hidden>
        <select id ="categoryDropdown" onchange="processCategory(this.value, '${intent}')">
          <option disabled hidden selected> Select Category </option>
          ${dropDownOptions}
        </select>
    </div> 
`;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideCategorySelect(){
  enableChatBoxInput();
  const selectCategory = document.getElementById('btnCont-category');
  if (selectCategory){
    // selectCategory.style.display = "none";
    selectCategory.remove();
  }
}

function processCategory(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideCategorySelect();
  processCreateTicketIntent(intent);
}


// ====================================================================================
function showSubcategory(header,subcategory,intent) {
  disableChatboxInput()
  console.log('Before Parsing: ', subcategory);
  let aiResponseElement = "";
  let parsedSubCategory = JSON.parse(subcategory);
  console.log('After Parsing: ', parsedSubCategory);

  let dropDownOptions = "";
  parsedSubCategory.forEach(key => {
    dropDownOptions += `<option value="${key}">${key}</option>`;
  });

  if (header === "subcategory"){
    aiResponseElement = `
    <div class="cont-subcategory" id="btnCont-subcategory" hidden>
        <select id ="subcategoryDropdown" onchange="processSubcategory(this.value, '${intent}')">
          <option disabled hidden selected> Select Subcategory </option>
          ${dropDownOptions}
        </select>
    </div> 
`;
  }

  chatboxMessageWrapper.insertAdjacentHTML("beforeend", aiResponseElement);
  scrollBottom();
}


function hideSubCategorySelect(){
  enableChatBoxInput();
  const selectSubcategory = document.getElementById('btnCont-subcategory');
  if (selectSubcategory){
    // selectSubcategory.style.display = "none";
    selectSubcategory.remove();
  }
}

function processSubcategory(key,intent){
  const userMessageTxtArea = document.getElementById("userMessage");
  userMessageTxtArea.value = key;
  hideSubCategorySelect();
  processCreateTicketIntent(intent);
}