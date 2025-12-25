class InterviewAssistant {
    constructor() {
        this.selectedCompany = null;
        this.selectedRole = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadMicrophones();
        await this.loadCompanies();
        this.updateUI();
    }

    setupEventListeners() {
        document.getElementById('reset-btn').addEventListener('click', () => this.reset());
        
        document.querySelectorAll('.content-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const section = e.target.dataset.section;
                this.loadContent(section);
            });
        });

        document.getElementById('voice-btn').addEventListener('click', () => this.toggleRecording());
        
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        document.getElementById('stop-recording').addEventListener('click', () => this.stopRecording());
    }

    async loadMicrophones() {
        try {
            const response = await fetch('/api/microphones');
            const microphones = await response.json();
            const select = document.getElementById('microphone-select');
            
            // Clear existing options except auto-detect
            const options = select.querySelectorAll('option:not([value="auto"])');
            options.forEach(option => option.remove());
            
            microphones.forEach(mic => {
                const option = document.createElement('option');
                option.value = mic.index;
                option.textContent = mic.name;
                select.appendChild(option);
            });
            
            console.log('Loaded microphones:', microphones);
        } catch (error) {
            console.warn('Could not load microphones:', error);
        }
    }

    async loadCompanies() {
        try {
            const response = await fetch('/api/companies');
            const companies = await response.json();
            console.log('Loaded companies:', companies);
            this.renderCompanyButtons(companies);
        } catch (error) {
            console.error('Error loading companies:', error);
            this.showNoCompaniesMessage();
        }
    }

    renderCompanyButtons(companies) {
        const container = document.getElementById('company-buttons');
        container.innerHTML = '';
        
        if (companies.length === 0) {
            this.showNoCompaniesMessage();
            return;
        }
        
        companies.forEach(company => {
            const button = document.createElement('button');
            button.className = 'stColumnButton';
            button.textContent = `🏢 ${company}`;
            button.addEventListener('click', () => this.selectCompany(company));
            container.appendChild(button);
        });
    }

    showNoCompaniesMessage() {
        const container = document.getElementById('company-buttons');
        container.innerHTML = '<div class="stEmptyState">No companies found in database</div>';
    }

    async selectCompany(company) {
        this.selectedCompany = company;
        this.selectedRole = null;
        
        try {
            const response = await fetch(`/api/roles/${encodeURIComponent(company)}`);
            const roles = await response.json();
            this.renderRoleButtons(roles);
        } catch (error) {
            console.error('Error loading roles:', error);
            this.showNoRolesMessage();
        }
        
        this.updateUI();
    }

    renderRoleButtons(roles) {
        const container = document.getElementById('role-buttons');
        container.innerHTML = '';
        
        if (roles.length === 0) {
            this.showNoRolesMessage();
            return;
        }
        
        roles.forEach(role => {
            const button = document.createElement('button');
            button.className = 'stColumnButton';
            button.textContent = `👨‍💼 ${role}`;
            button.addEventListener('click', () => this.selectRole(role));
            container.appendChild(button);
        });
    }

    showNoRolesMessage() {
        const container = document.getElementById('role-buttons');
        container.innerHTML = '<div class="stEmptyState">No roles found for this company</div>';
    }

    selectRole(role) {
        this.selectedRole = role;
        this.updateUI();
    }

    updateUI() {
        // Update sidebar selection status
        document.getElementById('selected-company').textContent = 
            this.selectedCompany || 'None selected';
        document.getElementById('selected-role').textContent = 
            this.selectedRole || 'None selected';

        // Update main content visibility
        const companySection = document.getElementById('company-selection');
        const roleSection = document.getElementById('role-selection');
        const readySection = document.getElementById('ready-status');
        const contentCategories = document.getElementById('content-categories');
        const chatInputArea = document.getElementById('chat-input-area');

        if (this.selectedCompany && !this.selectedRole) {
            // Show role selection
            companySection.style.display = 'none';
            roleSection.style.display = 'block';
            readySection.style.display = 'none';
            contentCategories.style.display = 'none';
            chatInputArea.style.display = 'none';
        } else if (this.selectedCompany && this.selectedRole) {
            // Show ready state and enable chat
            companySection.style.display = 'none';
            roleSection.style.display = 'none';
            readySection.style.display = 'block';
            contentCategories.style.display = 'block';
            chatInputArea.style.display = 'block';
            
            // Clear empty state message
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages.querySelector('.stEmptyState')) {
                chatMessages.innerHTML = '';
            }
            
            document.getElementById('ready-text').textContent = 
                `Ready: ${this.selectedRole} at ${this.selectedCompany}`;
        } else {
            // Show company selection
            companySection.style.display = 'block';
            roleSection.style.display = 'none';
            readySection.style.display = 'none';
            contentCategories.style.display = 'none';
            chatInputArea.style.display = 'none';
        }
    }

    async loadContent(sectionType) {
        if (!this.selectedCompany || !this.selectedRole) return;

        try {
            const response = await fetch('/api/content', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: this.selectedCompany,
                    role: this.selectedRole,
                    section_type: sectionType
                })
            });

            const data = await response.json();
            
            const sectionNames = {
                'interview_questions': '📌 Interview Questions',
                'study_material': '📚 Study Material',
                'tips': '💡 Tips',
                'mock_interview': '🎯 Mock Interview',
                'common_mistakes': '⚠️ Common Mistakes'
            };
            
            this.addMessage('user', `Clicked: ${sectionNames[sectionType]}`);
            this.addMessage('assistant', data.content);
        } catch (error) {
            console.error('Error loading content:', error);
            this.addMessage('assistant', '❌ Failed to load content');
        }
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message || !this.selectedCompany || !this.selectedRole) return;

        this.addMessage('user', message);
        input.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: message,
                    company: this.selectedCompany,
                    role: this.selectedRole
                })
            });

            const data = await response.json();
            
            if (data.error) {
                this.addMessage('assistant', `❌ Error: ${data.error}`);
            } else {
                this.addMessage('assistant', `🤖 **AI Response:**\n\n${data.response}`);
            }
        } catch (error) {
            this.addMessage('assistant', `❌ Error: ${error.message}`);
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            console.log('Requesting microphone access...');
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            console.log('Microphone access granted');
            
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            this.audioChunks = [];
            this.isRecording = true;

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                console.log('Recording stopped, processing audio...');
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                console.log('Audio blob created, size:', audioBlob.size);
                await this.processVoiceInput(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start(1000); // Record in 1-second chunks
            document.getElementById('recording-modal').style.display = 'flex';
            console.log('Recording started...');

        } catch (error) {
            console.error('Recording error:', error);
            alert(`Failed to start recording: ${error.message}\nPlease check microphone permissions.`);
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            console.log('Stopping recording...');
            this.mediaRecorder.stop();
            this.isRecording = false;
            document.getElementById('recording-modal').style.display = 'none';
        }
    }

    async processVoiceInput(audioBlob) {
        try {
            console.log('Processing voice input...');
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');

            const response = await fetch('/api/speech-to-text', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            console.log('Speech-to-text response:', data);
            
            if (data.error) {
                this.addMessage('assistant', `❌ Voice Error: ${data.error}`);
            } else if (data.text && data.text !== 'No speech detected') {
                this.addMessage('user', `🎤 **Voice Input:** ${data.text}`);
                await this.sendChatMessage(data.text);
            } else {
                this.addMessage('assistant', '❌ No speech detected. Please try again.');
            }
        } catch (error) {
            console.error('Voice processing error:', error);
            this.addMessage('assistant', `❌ Voice processing failed: ${error.message}`);
        }
    }

    async sendChatMessage(message) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: message,
                    company: this.selectedCompany,
                    role: this.selectedRole
                })
            });

            const data = await response.json();
            
            if (data.error) {
                this.addMessage('assistant', `❌ Error: ${data.error}`);
            } else {
                this.addMessage('assistant', `🤖 **AI Response:**\n\n${data.response}`);
            }
        } catch (error) {
            this.addMessage('assistant', `❌ Error: ${error.message}`);
        }
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('chat-messages');
        
        // Remove empty state if present
        const emptyState = messagesContainer.querySelector('.stEmptyState');
        if (emptyState) {
            emptyState.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `stChatMessage ${role}`;
        
        // Convert markdown-like formatting to HTML
        const formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = formattedContent;
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    reset() {
        this.selectedCompany = null;
        this.selectedRole = null;
        
        // Clear chat messages and restore empty state
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '<div class="stEmptyState">Select a company and role to start chatting</div>';
        
        // Reset input
        document.getElementById('chat-input').value = '';
        
        this.updateUI();
        this.loadCompanies();
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new InterviewAssistant();
});
