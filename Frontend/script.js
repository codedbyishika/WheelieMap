const API_BASE = "http://127.0.0.1:5000"; // map + DB backend
const AI_BASE  = "http://127.0.0.1:7000"; // chatbot backend

document.addEventListener("DOMContentLoaded", function() {

    // --- Mobile Navigation ---
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (mobileMenuToggle && navLinks) {
        mobileMenuToggle.addEventListener('click', () => {
            document.body.classList.toggle('nav-open');
            navLinks.classList.toggle('active');
        });
    }

    // --- CHATBOT WIDGET SETUP ---

    const launcher   = document.getElementById('safety-chat-launcher');
    const panel      = document.getElementById('safety-chat-panel');
    const closeBtn   = document.getElementById('chat-close-btn');
    const messagesEl = document.getElementById('chat-messages');
    const inputEl    = document.getElementById('chat-input');
    const sendBtn    = document.getElementById('chat-send-btn');

    function appendMessage(text, sender) {
        if (!messagesEl) return;
        const div = document.createElement('div');
        div.className = sender === 'user' ? 'user-msg' : 'bot-msg';
        div.innerHTML = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function openChat() {
        if (!panel) return;
        panel.style.display = 'flex';
        if (inputEl) inputEl.focus();
    }

    function closeChat() {
        if (!panel) return;
        panel.style.display = 'none';
    }

    if (launcher) {
        launcher.addEventListener('click', openChat);
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', closeChat);
    }

    function sendMessage() {
        if (!inputEl) return;
        const userText = inputEl.value.trim();
        if (!userText) return;

        appendMessage(userText, 'user');
        inputEl.value = '';

        fetch(`${AI_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText })
        })
        .then(res => res.json())
        .then(data => {
            appendMessage(data.reply, 'bot');
        })
        .catch(err => {
            console.error('chat error:', err);
            appendMessage("Follow a well lit and main pathways to your destination.", 'bot');
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    if (inputEl) {
        inputEl.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // --- Lead Magnet Modal (optional marketing feature) ---
    const leadMagnetModal = document.getElementById('lead-magnet-modal');
    if (leadMagnetModal) {
        const closeModalButtons = leadMagnetModal.querySelectorAll('.close-modal');
        const modalAlreadyShown = localStorage.getItem('u4uModalClosed');

        const showModal = () => {
            if (!modalAlreadyShown) {
                leadMagnetModal.classList.add('show');
            }
        };

        const closeModal = () => {
            localStorage.setItem('u4uModalClosed', 'true');
            leadMagnetModal.classList.remove('show');
        };

        setTimeout(showModal, 5000);

        closeModalButtons.forEach(button => {
            button.addEventListener('click', closeModal);
        });

        leadMagnetModal.addEventListener('click', (e) => {
            if (e.target === leadMagnetModal) {
                closeModal();
            }
        });
    }

    // --- FAQ Accordion ---
    const faqCards = document.querySelectorAll('.faq-card');
    if (faqCards) {
        faqCards.forEach(card => {
            const question = card.querySelector('.faq-question');
            const answer = card.querySelector('.faq-answer');

            question.addEventListener('click', () => {
                const isActive = card.classList.contains('active');

                faqCards.forEach(otherCard => {
                    if (otherCard !== card) {
                        otherCard.classList.remove('active');
                        otherCard.querySelector('.faq-answer').style.maxHeight = null;
                    }
                });

                if (!isActive) {
                    card.classList.add('active');
                    answer.style.maxHeight = answer.scrollHeight + 'px';
                } else {
                    card.classList.remove('active');
                    answer.style.maxHeight = null;
                }
            });
        });
    }

    // --- Fade-in animations ---
    const fadeUpElements = document.querySelectorAll('.fade-in-up');
    if (fadeUpElements) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = `fadeInUp 0.8s ease-out forwards`;
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        fadeUpElements.forEach(el => observer.observe(el));
    }

    // --- SAFETY MAP SECTION ---
    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        return; // page doesn't have a map section (like on FAQ page)
    }

    console.log("Initializing map...");

    if (typeof L === 'undefined') {
        console.error("Leaflet is not loaded. Include Leaflet <script> and <link>.");
        return;
    }

    // hazard colors
    const colors = {
      'Slippery': 'blue',
      'Low Lighting': 'yellow',
      'Isolated': 'red',
      'Crowded Area': 'purple',
      'Low Visibility': 'gray',
      'Others': 'black'
    };

    // track which hazard type user chose
    let selectedType = null;
    const hazardButtons = document.querySelectorAll('#controls button');
    hazardButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            hazardButtons.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            selectedType = btn.dataset.type || btn.innerText.trim();
            console.log("Selected hazard:", selectedType);
        });
    });

    // init map
    const map = L.map('map').setView([0, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var greenIcon = new L.Icon({
      iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
      shadowSize: [41, 41]
    });

    // center map to user when possible
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            const { latitude, longitude } = pos.coords;
            map.setView([latitude, longitude], 15);

            const userMarker = L.marker([latitude, longitude], {
            icon: greenIcon
            }).addTo(map);
            userMarker.bindPopup("📍 You are here").openPopup();
        }, err => {
            console.warn("Could not get current location:", err.message);
            map.setView([37.7749, -122.4194], 13);
        });
    }

    function drawMarker(lat, lng, type, description, timestamp) {
        const color = colors[type] || 'gray';
        const prettyDesc = description || 'No description';
        const prettyTime = timestamp ? `<br><small>${timestamp}</small>` : '';

        L.circleMarker([lat, lng], {
            radius: 8,
            color: color,
            fillColor: color,
            fillOpacity: 0.8
        })
        .addTo(map)
        .bindPopup(`<b>${type}</b><br>${prettyDesc}${prettyTime}`);
    }

    // Load existing reports
    fetch(`${API_BASE}/reports`, {
        method: 'GET'
    })
    .then(res => res.json())
    .then(data => {
        console.log("Loaded reports from server:", data);

        if (!Array.isArray(data)) {
            console.error("Server returned error instead of list:", data);
            return;
        }

        data.forEach(loc => {
            drawMarker(loc.lat, loc.lng, loc.type, loc.description, loc.timestamp);
        });
    })
    .catch(err => {
        console.error("Error fetching reports:", err);
    });

    // Click map to submit new hazard
    map.on('click', e => {
        console.log("Map clicked at:", e.latlng);

        if (!selectedType) {
            alert('Please select a hazard type first!');
            return;
        }

        const description = prompt("Add a short description (optional):") || "";
        const { lat, lng } = e.latlng;

        console.log("Submitting report:", {
            lat,
            lng,
            type: selectedType,
            description
        });

        // optimistic UI
        drawMarker(lat, lng, selectedType, description, new Date().toISOString());

        // persist to DB
        fetch(`${API_BASE}/report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: lat,
                lng: lng,
                type: selectedType,
                description: description
            })
        })
        .then(res => res.json())
        .then(data => {
            console.log("Server says:", data);
        })
        .catch(err => {
            console.error("Error sending report:", err);
            alert("Could not save to server.");
        });
    });
});
