/**
 * Enterprise Data Quality Platform - Dashboard
 */

const API_BASE_URL = "http://localhost:8000/api";

document.addEventListener("DOMContentLoaded", () => {
    loadDashboardData();
    loadRecentDatasets();
});

async function loadDashboardData() {
    try {
        const datasetsResponse = await fetch(`${API_BASE_URL}/datasets`, {
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
            },
        });

        if (!datasetsResponse.ok) {
            console.error("Failed to load datasets");
            return;
        }

        const datasetsData = await datasetsResponse.json();
        const datasets = datasetsData.items || [];

        document.getElementById("total-datasets").textContent = datasets.length;

        const validatedCount = datasets.filter((d) => d.quality_score).length;
        const avgQuality =
            datasets.length > 0
                ? (
                      datasets.reduce((sum, d) => sum + (d.quality_score || 0), 0) /
                      datasets.length
                  ).toFixed(1)
                : 0;

        document.getElementById("validated-count").textContent = validatedCount;
        document.getElementById("avg-quality").textContent = avgQuality + "%";
        
        const issuesCount = datasets.reduce((sum, d) => {
            return sum + (d.validation_issues?.length || 0);
        }, 0);
        document.getElementById("issues-count").textContent = issuesCount;
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

/**
 * Load recent datasets and populate table
 */
async function loadRecentDatasets() {
    try {
        const response = await fetch(`${API_BASE_URL}/datasets?page=1&page_size=10`, {
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
            },
        });

        if (!response.ok) {
            console.error("Failed to load datasets");
            return;
        }

        const data = await response.json();
        const datasets = data.items || [];
        const tableBody = document.getElementById("datasets-table");

        if (datasets.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="7" class="text-center text-muted">No datasets found</td></tr>';
            return;
        }

        tableBody.innerHTML = datasets
            .map(
                (dataset) => `
            <tr>
                <td>
                    <strong>${dataset.name}</strong>
                    ${dataset.description ? `<br><small class="text-muted">${dataset.description}</small>` : ""}
                </td>
                <td><span class="badge bg-info">${dataset.file_type.toUpperCase()}</span></td>
                <td>${dataset.total_rows?.toLocaleString() || "N/A"}</td>
                <td>
                    ${
                        dataset.quality_score
                            ? `<div class="progress" style="height: 20px;">
                        <div class="progress-bar ${getQualityColor(dataset.quality_score)}" style="width: ${dataset.quality_score}%">
                            ${dataset.quality_score.toFixed(1)}%
                        </div>
                    </div>`
                            : "Pending"
                    }
                </td>
                <td>
                    ${
                        dataset.is_cleaned
                            ? '<span class="status-badge success">Cleaned</span>'
                            : '<span class="status-badge warning">Raw</span>'
                    }
                </td>
                <td>${new Date(dataset.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewDataset('${dataset.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `
            )
            .join("");
    } catch (error) {
        console.error("Error loading datasets:", error);
    }
}

function getQualityColor(score) {
    if (score >= 80) return "bg-success";
    if (score >= 60) return "bg-warning";
    return "bg-danger";
}

function viewDataset(datasetId) {
    window.location.href = `/#/datasets/${datasetId}`;
}

function getAuthToken() {
    return localStorage.getItem("access_token") || "";
}

function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

/**
 * Upload dataset from form
 */
async function uploadDataset(formData) {
    try {
        const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
            },
            body: formData,
        });

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        const result = await response.json();
        showAlert("Dataset uploaded successfully!", "success");
        loadRecentDatasets();
        return result;
    } catch (error) {
        console.error("Upload error:", error);
        showAlert("Failed to upload dataset", "danger");
    }
}

/**
 * Display dismissable alert message
 */
function showAlert(message, type = "info") {
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector("main") || document.body;
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function formatNumber(num) {
    return num?.toLocaleString() || "0";
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}
