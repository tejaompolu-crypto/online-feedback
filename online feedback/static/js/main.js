document.addEventListener("DOMContentLoaded", function () {
    var feedbackForm = document.getElementById("feedback-form");
    var loginForm = document.getElementById("login-form");
    var dashboardEl = document.getElementById("admin-dashboard");

    if (feedbackForm) {
        initFeedbackForm();
    }
    if (loginForm) {
        initLoginForm();
    }
    if (dashboardEl) {
        initDashboard();
    }
});

/* ===== Helpers ===== */
function showToast(message, type) {
    var container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    var toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

function getCsrfToken() {
    var meta = document.querySelector("meta[name='csrf-token']");
    return meta ? meta.getAttribute("content") : "";
}

/* ===== Feedback Form ===== */
function initFeedbackForm() {
    var form = document.getElementById("feedback-form");
    var submitBtn = document.getElementById("submit-btn");

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        // Reset previous errors
        var groups = form.querySelectorAll(".form-group");
        for (var i = 0; i < groups.length; i++) {
            groups[i].querySelector(".input-error") && groups[i].querySelector(".input-error").classList.remove("input-error");
            var errText = groups[i].querySelector(".error-text");
            if (errText) errText.classList.remove("visible");
        }

        var name = (document.getElementById("name").value || "").trim();
        var email = (document.getElementById("email").value || "").trim();
        var feedbackText = (document.getElementById("feedback-text").value || "").trim();
        var category = document.getElementById("category").value;
        var ratingInput = document.querySelector('input[name="rating"]:checked');

        var valid = true;

        if (!name) {
            markError("name", "Name is required");
            valid = false;
        }
        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            if (email) markError("email", "Enter a valid email");
            else markError("email", "Email is required");
            valid = false;
        }
        if (!ratingInput) {
            document.getElementById("rating-error").classList.add("visible");
            valid = false;
        }
        if (!feedbackText) {
            markError("feedback-text", "Feedback text is required");
            valid = false;
        }

        if (!valid) return;

        var rating = parseInt(ratingInput.value);
        var data = {
            name: name,
            email: email,
            rating: rating,
            feedback_text: feedbackText,
            category: category
        };

        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting...";

        fetch("/api/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        })
        .then(function (res) { return res.json(); })
        .then(function (result) {
            if (result.success) {
                form.reset();
                showToast("Feedback submitted successfully!", "success");
            } else {
                showToast(result.error || "Submission failed", "error");
            }
        })
        .catch(function () {
            showToast("Network error. Please try again.", "error");
        })
        .finally(function () {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Feedback";
        });
    });
}

function markError(fieldId, message) {
    var el = document.getElementById(fieldId);
    if (el) {
        el.classList.add("input-error");
        var group = el.closest(".form-group");
        if (group) {
            var errText = group.querySelector(".error-text");
            if (errText) errText.textContent = message;
            if (errText) errText.classList.add("visible");
        }
    }
}

/* ===== Admin Login ===== */
function initLoginForm() {
    var form = document.getElementById("login-form");
    var input = document.getElementById("secret-key");
    var errorEl = document.getElementById("login-error-text");

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var key = (input.value || "").trim();
        errorEl.style.display = "none";
        input.classList.remove("shake");

        fetch("/admin/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ secret_key: key })
        })
        .then(function (res) {
            if (res.ok) return res.json();
            return res.json().then(function (d) { throw new Error(d.error || "Login failed"); });
        })
        .then(function () {
            window.location.href = "/admin/dashboard";
        })
        .catch(function (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = "block";
            input.classList.add("shake");
            setTimeout(function () { input.classList.remove("shake"); }, 400);
        });
    });
}

/* ===== Admin Dashboard ===== */
function initDashboard() {
    // Delete buttons
    var deleteBtns = document.querySelectorAll(".delete-btn");
    for (var i = 0; i < deleteBtns.length; i++) {
        deleteBtns[i].addEventListener("click", function () {
            var id = this.getAttribute("data-id");
            if (!confirm("Delete this feedback? This cannot be undone.")) return;

            var btn = this;
            btn.disabled = true;
            btn.textContent = "Deleting...";

            fetch("/admin/response/" + id, {
                method: "DELETE",
                headers: { "X-CSRF-Token": getCsrfToken() }
            })
            .then(function (res) { return res.json(); })
            .then(function (result) {
                if (result.success) {
                    var row = btn.closest("tr");
                    if (row) row.remove();
                    showToast("Feedback deleted", "success");
                    // Check if table is now empty
                    var rows = document.querySelectorAll("#feedback-table tbody tr");
                    var visibleRows = 0;
                    for (var j = 0; j < rows.length; j++) {
                        if (!rows[j].classList.contains("empty-state-row")) visibleRows++;
                    }
                    if (visibleRows === 0 && rows.length === 0) {
                        var tbody = document.querySelector("#feedback-table tbody");
                        var emptyTr = document.createElement("tr");
                        emptyTr.innerHTML = '<td colspan="8" class="empty-state">No feedback found</td>';
                        tbody.appendChild(emptyTr);
                    }
                } else {
                    showToast(result.error || "Delete failed", "error");
                    btn.disabled = false;
                    btn.textContent = "Delete";
                }
            })
            .catch(function () {
                showToast("Network error", "error");
                btn.disabled = false;
                btn.textContent = "Delete";
            });
        });
    }

    // Reply buttons
    var replyBtns = document.querySelectorAll(".reply-btn");
    for (var j = 0; j < replyBtns.length; j++) {
        replyBtns[j].addEventListener("click", function () {
            var id = this.getAttribute("data-id");
            var area = document.querySelector('.reply-area[data-id="' + id + '"]');
            if (!area) return;
            area.classList.toggle("visible");
            var textarea = area.querySelector("textarea");
            if (textarea) textarea.focus();
        });
    }

    // Reply submit buttons
    var replySubmitBtns = document.querySelectorAll(".reply-submit-btn");
    for (var k = 0; k < replySubmitBtns.length; k++) {
        replySubmitBtns[k].addEventListener("click", function () {
            var id = this.getAttribute("data-id");
            var area = document.querySelector('.reply-area[data-id="' + id + '"]');
            var textarea = area.querySelector("textarea");
            var replyText = (textarea.value || "").trim();
            if (!replyText) return;

            var btn = this;
            btn.disabled = true;
            btn.textContent = "Saving...";

            fetch("/admin/response/" + id, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": getCsrfToken()
                },
                body: JSON.stringify({ reply: replyText })
            })
            .then(function (res) { return res.json(); })
            .then(function (result) {
                if (result.success) {
                    var existing = area.querySelector(".reply-existing");
                    if (!existing) {
                        var div = document.createElement("div");
                        div.className = "reply-existing";
                        div.textContent = replyText;
                        area.insertBefore(div, area.firstChild);
                    } else {
                        existing.textContent = replyText;
                    }
                    showToast("Reply saved", "success");
                    area.classList.remove("visible");
                    textarea.value = "";
                    btn.disabled = false;
                    btn.textContent = "Save";
                } else {
                    showToast(result.error || "Save failed", "error");
                    btn.disabled = false;
                    btn.textContent = "Save";
                }
            })
            .catch(function () {
                showToast("Network error", "error");
                btn.disabled = false;
                btn.textContent = "Save";
            });
        });
    }

    // Logout button
    var logoutForm = document.getElementById("logout-form");
    if (logoutForm) {
        logoutForm.addEventListener("submit", function (e) {
            // Don't send CSRF for logout, it's handled separately
        });
    }

    // Apply filters button
    var applyFilters = document.getElementById("apply-filters");
    if (applyFilters) {
        applyFilters.addEventListener("click", function () {
            applyFilterChanges();
        });
    }
}

function applyFilterChanges() {
    var cat = document.getElementById("filter-category").value;
    var rat = document.getElementById("filter-rating").value;
    var searchVal = document.getElementById("filter-search").value;

    var params = new URLSearchParams(window.location.search);
    if (cat && cat !== "all") params.set("category", cat);
    else params.delete("category");
    if (rat && rat !== "all") params.set("rating", rat);
    else params.delete("rating");
    if (searchVal.trim()) params.set("search", searchVal.trim());
    else params.delete("search");
    params.set("page", "1");

    window.location.search = params.toString();
}
