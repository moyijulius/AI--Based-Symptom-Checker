$(document).ready(function () {
    // Real-time input validation
    document.getElementById('symptoms').addEventListener('input', function (e) {
        const input = e.target.value;
        const errorMessage = document.getElementById('errorMessage');
        if (/[^a-zA-Z,_\s]/.test(input)) {
            errorMessage.textContent = "Only letters, commas, spaces, and underscores are allowed.";
        } else {
            errorMessage.textContent = "";
        }
    });

    $("#symptom-form").on("submit", function (e) {
        e.preventDefault();

        const symptoms = $("#symptoms").val().trim();
        const errorMessage = $("#errorMessage");

        // Validate the input first
        if (symptoms === "") {
            errorMessage.text("Input symptoms first");
            return; // Stop further processing
        } else {
            errorMessage.text(""); // Clear the error message
        }

        // Proceed to send the request if validation passes
        $.ajax({
            url: "/predict",
            type: "POST",
            data: { symptoms: symptoms },
            success: function (response) {
                if (response.error) {
                    alert(response.error); // Show error from server
                } else {
                    const disease = response.disease;
                    $("#resultText").text(`Predicted Disease: ${disease}`);
                    $("#resultModal").modal("show");

                    // Add buttons for additional details
                    $("#dynamic-buttons").html(`
                        <h1>Our AI Systems</h1>
                        <div class="floating-buttons-container">
                            <button class="btn btn-info bg-warning" id="medication-btn">Medication</button>
                            <button class="btn btn-info bg-success" id="description-btn">Description</button>
                            <button class="btn btn-info bg-danger" id="precaution-btn">Precaution</button>
                            <button class="btn btn-info bg-info" id="diets-btn">Diets</button>
                            <button class="btn btn-info bg-primary" id="workout-btn">Workout</button>
                        </div>
                    `);

                    // Fetch and display details when buttons are clicked
                    $("#medication-btn").click(function () {
                        fetchDetails(disease, "medication");
                    });
                    $("#description-btn").click(function () {
                        fetchDetails(disease, "description");
                    });
                    $("#precaution-btn").click(function () {
                        fetchDetails(disease, "precautions_df");
                    });
                    $("#diets-btn").click(function () {
                        fetchDetails(disease, "diets");
                    });
                    $("#workout-btn").click(function () {
                        fetchDetails(disease, "workout_df");
                    });
                }
            },
            error: function () {
                alert("An error occurred. Please try again.");
            }
        });
    });

    function fetchDetails(disease, type) {
        $.ajax({
            url: `/details/${disease}`,
            type: "GET",
            success: function (response) {
                if (response.error) {
                    alert(response.error);
                } else {
                    const info = response[type];
                    const modalId =
                        type === "medication" ? "#medicationModal" :
                        type === "description" ? "#descriptionModal" :
                        type === "precautions_df" ? "#precautionModal" :
                        type === "diets" ? "#dietsModal" :
                        "#workoutModal";

                    $(modalId).find(".modal-body p").text(info);
                    $(modalId).modal("show");
                }
            },
            error: function () {
                alert("Failed to fetch details. Please try again.");
            }
        });
    }
});
// Wait for the page to fully load
document.addEventListener("DOMContentLoaded", function() {
    // Select all flash messages
    let flashMessages = document.querySelectorAll(".alert");

    flashMessages.forEach(function(message) {
        // Set a timeout to remove the message after 3 seconds (3000ms)
        setTimeout(function() {
            message.style.transition = "opacity 0.5s";
            message.style.opacity = "0"; // Fade out
            setTimeout(() => message.remove(), 500); // Remove from DOM
        }, 3000);
    });
});


