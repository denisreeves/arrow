// Global variables
let emailList = [];
let currentListId = null;

// Ensure user is logged in before accessing the main app
document.addEventListener('DOMContentLoaded', function () {
    // Check if we're on the login page
    const isLoginPage = window.location.pathname.includes('/login');

    // Get user from localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    // If on login page, set up login/register functionality
    if (isLoginPage) {
        setupLoginPage();
        // If user is already logged in, redirect to main page
        if (user.token) {
            window.location.href = '/';
        }
        return;
    }

    // Main app page - check authentication
    if (!user.token) {
        window.location.href = '/login';
        return;
    }

    // Verify token is valid by making a request to a protected endpoint
    fetch('/user-profile', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${user.token}`,
            'Content-Type': 'application/json',
        },
    })
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                // Invalid token, redirect to login
                localStorage.removeItem('user');
                window.location.href = '/login';
            } else {
                // Display user info in the sidebar
                const userInfoElement = document.createElement('div');
                userInfoElement.className = 'user-info';
                userInfoElement.innerHTML = `
                    <p>Welcome, ${data.user.name}</p>
                    <button id="logout-btn">Logout</button>
                    <button id="data-visualization-btn" class="data-viz-button">📊 Data Visualization</button>
                `;
                document.querySelector('.sidebar').appendChild(userInfoElement);

                // Add logout functionality
                document.getElementById('logout-btn').addEventListener('click', function () {
                    localStorage.removeItem('user');
                    window.location.href = '/login';
                });

                // Add data visualization button functionality
                document.getElementById('data-visualization-btn').addEventListener('click', function () {
                    window.location.href = '/data-visualization'; // Redirect to the data visualization page
                });

                // Setup main app functionality
                setupMainApp();
            }
        })
        .catch((error) => {
            console.error('Error verifying token:', error);
            localStorage.removeItem('user');
            window.location.href = '/login';
        });
});

document.getElementById('statistics-tab-btn')?.addEventListener('click', function(e) {
    e.preventDefault();
    showTab('statistics-tab');
});
function loadStatistics() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('statistics-container').innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h5>Total Users: ${data.statistics.total_users}</h5>
                            <h5>Total Emails Sent: ${data.statistics.total_emails}</h5>
                        </div>
                    </div>
                `;
            } else {
                document.getElementById('statistics-container').innerHTML = `<p>Error: ${data.message}</p>`;
            }
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
            document.getElementById('statistics-container').innerHTML = `<p>Error loading statistics.</p>`;
        });
}

// Ensure the function runs when the "Statistics" tab is clicked
document.getElementById('statistics-tab-btn')?.addEventListener('click', function(e) {
    e.preventDefault();
    showTab('statistics-tab');
    loadStatistics(); // Fetch data when the tab is clicked
});
s

// Setup login page functionality
function setupLoginPage() {
    // Handle Login
    document.getElementById('login-button')?.addEventListener('click', async function () {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const errorElement = document.getElementById('login-error');
        const successElement = document.getElementById('login-success');

        errorElement.textContent = '';
        successElement.textContent = '';

        if (!email || !password) {
            errorElement.textContent = 'Please enter both email and password';
            return;
        }

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const result = await response.json();
            if (result.success) {
                successElement.textContent = 'Login successful! Redirecting...';

                localStorage.setItem(
                    'user',
                    JSON.stringify({
                        id: result.userId,
                        name: result.name,
                        email: result.email,
                        token: result.token,
                    })
                );

                // In the login success handling, after localStorage.setItem:
                if (result.isAdmin) {
                    setTimeout(() => {
                        window.location.href = '/admin';
                    }, 1500);
                } else {
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1500);
                }
            } else {
                errorElement.textContent = result.message || 'Invalid credentials';
            }
        } catch (error) {
            console.error('Error during login:', error);
            errorElement.textContent = 'An error occurred. Please try again.';
        }
    });

    // Handle Registration
    document.getElementById('register-button')?.addEventListener('click', async function () {
        const name = document.getElementById('register-name').value.trim();
        const email = document.getElementById('register-email').value.trim();
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('register-confirm-password').value;
        const errorElement = document.getElementById('register-error');
        const successElement = document.getElementById('register-success');

        errorElement.textContent = '';
        successElement.textContent = '';

        if (!name || !email || !password || !confirmPassword) {
            errorElement.textContent = 'Please fill in all fields';
            return;
        }

        if (password !== confirmPassword) {
            errorElement.textContent = 'Passwords do not match';
            return;
        }

        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password }),
            });

            const result = await response.json();
            if (result.success) {
                successElement.textContent = 'Registration successful! Please login.';
                setTimeout(() => {
                    document.getElementById('register-form').style.display = 'none';
                    document.getElementById('login-form').style.display = 'block';
                    document.getElementById('login-success').textContent = 'Registration successful! Please login.';
                }, 2000);
            } else {
                errorElement.textContent = result.message || 'Registration failed';
            }
        } catch (error) {
            console.error('Error during registration:', error);
            errorElement.textContent = 'An error occurred. Please try again.';
        }
    });

    // Toggle between login and registration forms
    document.getElementById('show-register')?.addEventListener('click', function () {
        document.getElementById('login-form').style.display = 'none';
        document.getElementById('register-form').style.display = 'block';
    });

    document.getElementById('show-login')?.addEventListener('click', function () {
        document.getElementById('register-form').style.display = 'none';
        document.getElementById('login-form').style.display = 'block';
    });
}

// Setup main app functionality
function setupMainApp() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    // File upload handler
    document.getElementById('file-upload')?.addEventListener('change', async function (e) {
        const file = e.target.files[0];
        if (!file) return;

        // Check file type
        const fileType = file.name.split('.').pop().toLowerCase();
        if (!['csv', 'xlsx', 'xls'].includes(fileType)) {
            alert('Please upload a CSV or Excel file');
            return;
        }

        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload-email-list', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${user.token}`,
                },
                body: formData,
            });

            const result = await response.json();

            if (result.success) {
                // Store the list ID
                currentListId = result.list_id;

                // Store the email list
                emailList = result.emails;

                // Display the emails
                displayEmailList(emailList);

                // Show the email list container
                document.getElementById('email-list-container').style.display = 'block';
            } else {
                alert(result.message || 'Error uploading file');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert('An error occurred. Please try again.');
        }
    });

    // Select all emails
    document.getElementById('select-all')?.addEventListener('change', function (e) {
        const checkboxes = document.querySelectorAll('#email-list input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
            checkbox.checked = e.target.checked;
        });
    });

    // Generate email content with AI
    document.getElementById('generate-ai')?.addEventListener('click', async function () {
        const prompt = document.getElementById('ai-prompt').value.trim();

        if (!prompt) {
            alert('Please enter a prompt for the AI');
            return;
        }

        try {
            const response = await fetch('/generate-email', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${user.token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt }),
            });

            const result = await response.json();

            if (result.success) {
                // Display the generated content
                document.getElementById('ai-result').value = result.content;
                document.getElementById('ai-result-container').style.display = 'block';
            } else {
                alert(result.message || 'Error generating email content');
            }
        } catch (error) {
            console.error('Error generating email content:', error);
            alert('An error occurred. Please try again.');
        }
    });

    // Use generated AI content
    document.getElementById('use-ai-content')?.addEventListener('click', function () {
        const content = document.getElementById('ai-result').value;
        document.getElementById('email-body').value = content;
    });

    // Send emails
    document.getElementById('send-emails')?.addEventListener('click', async function () {
        if (!currentListId) {
            alert('Please upload an email list first');
            return;
        }

        const senderEmail = document.getElementById('sender-email').value.trim();
        const senderPassword = document.getElementById('sender-password').value;
        const smtpServer = document.getElementById('smtp-server').value.trim();
        const smtpPort = document.getElementById('smtp-port').value.trim();
        const subject = document.getElementById('email-subject').value.trim();
        const bccEmails = document.getElementById('bcc-email').value.trim();
        const body = document.getElementById('email-body').value.trim();

        if (!senderEmail || !senderPassword || !smtpServer || !smtpPort || !subject || !body) {
            alert('Please fill in all required fields');
            return;
        }

        try {
            const response = await fetch('/send-emails', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${user.token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    list_id: currentListId,
                    sender_email: senderEmail,
                    sender_password: senderPassword,
                    smtp_server: smtpServer,
                    smtp_port: smtpPort,
                    subject: subject,
                    bcc_emails: bccEmails,
                    body: body,
                }),
            });

            const result = await response.json();

            if (result.success) {
                alert(`Emails sent: ${result.successful_count} successful, ${result.failed_count} failed`);
            } else {
                alert(result.message || 'Error sending emails');
            }
        } catch (error) {
            console.error('Error sending emails:', error);
            alert('An error occurred. Please try again.');
        }
    });
}

// Display email list in the UI
function displayEmailList(emails) {
    const emailListElement = document.getElementById('email-list');
    const emailCountElement = document.getElementById('email-count');

    // Clear the list
    emailListElement.innerHTML = '';

    // Update the count
    emailCountElement.textContent = emails.length;

    // Add each email to the list
    emails.forEach((item, index) => {
        const emailItem = document.createElement('div');
        emailItem.className = 'email-item';
        emailItem.innerHTML = `
            <label>
                <input type="checkbox" value="${index}" checked>
                ${item.name ? `${item.name} <${item.email}>` : item.email}
            </label>
        `;
        emailListElement.appendChild(emailItem);
    });
}