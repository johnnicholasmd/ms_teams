// ====================================================================================
// FOR Q&A
function processQandA() {
  if (isValid(textarea.value)) {
    const userMessage = textarea.value;
    var tempId = document.getElementById("temp-id").dataset.tempId;
    displaySentMessage(userMessage);
    displayTypingIndicator();
    textarea.value = "";
    textarea.rows = 1;
    textarea.focus();
    chatboxNoMessage.style.display = "none";
    userResponse = userResponse.replace(/[^\w\s]/g, "");

    fetch(`/q_and_a/${tempId}/${userResponse}/`, {
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
