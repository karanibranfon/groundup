// Syringly Cookie Utility

const SyringlyCookies = {
    // Cookie configuration
    defaults: {
        expires: 365, // days
        path: '/syringly/',
        sameSite: 'Lax'
    },

    // Set a cookie
    set(name, value, options = {}) {
        const settings = { ...this.defaults, ...options };
        let cookieString = `${encodeURIComponent(name)}=${encodeURIComponent(JSON.stringify(value))}`;
        
        if (settings.expires) {
            const date = new Date();
            date.setTime(date.getTime() + (settings.expires * 24 * 60 * 60 * 1000));
            cookieString += `; expires=${date.toUTCString()}`;
        }
        
        cookieString += `; path=${settings.path}`;
        
        if (settings.domain) {
            cookieString += `; domain=${settings.domain}`;
        }
        
        if (settings.sameSite) {
            cookieString += `; samesite=${settings.sameSite}`;
        }
        
        if (settings.secure) {
            cookieString += '; secure';
        }
        
        document.cookie = cookieString;
    },

    // Get a cookie
    get(name) {
        const nameEQ = `${encodeURIComponent(name)}=`;
        const cookies = document.cookie.split(';');
        
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.indexOf(nameEQ) === 0) {
                try {
                    return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
                } catch (e) {
                    return decodeURIComponent(cookie.substring(nameEQ.length));
                }
            }
        }
        return null;
    },

    // Delete a cookie
    delete(name, options = {}) {
        this.set(name, '', { ...options, expires: -1 });
    },

    // Check if cookie exists
    exists(name) {
        return this.get(name) !== null;
    }
};

// User Preferences Manager
const UserPreferences = {
    cookieName: 'syringly_prefs',
    
    defaults: {
        sort: 'newest',
        view: 'list', // list or grid
        showTags: true,
        pageSize: 20
    },
    
    get() {
        const stored = SyringlyCookies.get(this.cookieName);
        return { ...this.defaults, ...stored };
    },
    
    set(preferences) {
        const current = this.get();
        SyringlyCookies.set(this.cookieName, { ...current, ...preferences });
    },
    
    update(key, value) {
        const prefs = this.get();
        prefs[key] = value;
        SyringlyCookies.set(this.cookieName, prefs);
    },
    
    reset() {
        SyringlyCookies.delete(this.cookieName);
    }
};

// Recently Viewed Questions Manager
const RecentlyViewed = {
    cookieName: 'syringly_recently_viewed',
    maxItems: 10,
    
    get() {
        return SyringlyCookies.get(this.cookieName) || [];
    },
    
    add(questionId, title) {
        let items = this.get();
        
        // Remove if already exists
        items = items.filter(item => item.id !== questionId);
        
        // Add to beginning
        items.unshift({
            id: questionId,
            title: title,
            viewedAt: new Date().toISOString()
        });
        
        // Keep only maxItems
        items = items.slice(0, this.maxItems);
        
        SyringlyCookies.set(this.cookieName, items, { expires: 7 }); // 7 days
    },
    
    clear() {
        SyringlyCookies.delete(this.cookieName);
    }
};

// Draft Question Manager
const DraftQuestion = {
    cookieName: 'syringly_draft_question',
    saveDelay: 1000, // 1 second debounce
    timeout: null,
    
    get() {
        return SyringlyCookies.get(this.cookieName) || { title: '', body: '', tags: '' };
    },
    
    save(data) {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
            SyringlyCookies.set(this.cookieName, data, { expires: 7 }); // 7 days
            this.showSavedIndicator();
        }, this.saveDelay);
    },
    
    clear() {
        SyringlyCookies.delete(this.cookieName);
        this.hideSavedIndicator();
    },
    
    showSavedIndicator() {
        let indicator = document.getElementById('draft-saved');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.id = 'draft-saved';
            indicator.className = 'text-muted ms-2';
            indicator.style.fontSize = '12px';
            const input = document.getElementById('title');
            if (input) {
                input.parentElement.appendChild(indicator);
            }
        }
        indicator.textContent = 'Draft saved';
        setTimeout(() => {
            if (indicator) indicator.textContent = '';
        }, 2000);
    },
    
    hideSavedIndicator() {
        const indicator = document.getElementById('draft-saved');
        if (indicator) indicator.remove();
    }
};

// Anonymous Voting Tracker
const VoteTracker = {
    cookieName: 'syringly_votes',
    
    getVotes() {
        return SyringlyCookies.get(this.cookieName) || {};
    },
    
    hasVoted(contentType, objectId) {
        const key = `${contentType}_${objectId}`;
        const votes = this.getVotes();
        return key in votes;
    },
    
    getVote(contentType, objectId) {
        const key = `${contentType}_${objectId}`;
        const votes = this.getVotes();
        return votes[key] || 0;
    },
    
    recordVote(contentType, objectId, value) {
        const key = `${contentType}_${objectId}`;
        let votes = this.getVotes();
        votes[key] = value;
        SyringlyCookies.set(this.cookieName, votes, { expires: 365 }); // 1 year
    },
    
    removeVote(contentType, objectId) {
        const key = `${contentType}_${objectId}`;
        let votes = this.getVotes();
        delete votes[key];
        SyringlyCookies.set(this.cookieName, votes, { expires: 365 });
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Track recently viewed questions on question detail pages
    const questionDetail = document.querySelector('.question-detail');
    if (questionDetail) {
        const questionId = questionDetail.dataset.questionId;
        const questionTitle = document.querySelector('.question-header h1')?.textContent;
        if (questionId && questionTitle) {
            RecentlyViewed.add(parseInt(questionId), questionTitle.trim());
        }
    }
    
    // Restore draft question on ask page
    const askForm = document.querySelector('.ask-form');
    if (askForm) {
        const draft = DraftQuestion.get();
        const titleInput = document.getElementById('title');
        const bodyInput = document.getElementById('body');
        const tagsInput = document.getElementById('tags');
        
        if (titleInput && draft.title) {
            titleInput.value = draft.title;
        }
        if (bodyInput && draft.body) {
            bodyInput.value = draft.body;
        }
        if (tagsInput && draft.tags) {
            tagsInput.value = draft.tags;
        }
        
        // Auto-save on input
        [titleInput, bodyInput, tagsInput].forEach(input => {
            if (input) {
                input.addEventListener('input', () => {
                    DraftQuestion.save({
                        title: titleInput.value,
                        body: bodyInput.value,
                        tags: tagsInput.value
                    });
                });
            }
        });
        
        // Clear draft on submit
        askForm.addEventListener('submit', () => {
            DraftQuestion.clear();
        });
    }
    
    // Initialize vote buttons with cookie tracking
    initVoteButtons();
});

function initVoteButtons() {
    document.querySelectorAll('.vote-btn').forEach(btn => {
        const type = btn.dataset.type;
        const id = btn.dataset.id;
        const contentType = type === 'question' ? 'Q' : 'A';
        
        // Check if already voted (from cookie)
        const previousVote = VoteTracker.getVote(contentType, id);
        if (previousVote === 1) {
            btn.classList.add('voted-up');
        } else if (previousVote === -1) {
            btn.classList.add('voted-down');
        }
        
        btn.addEventListener('click', async function() {
            const vote = parseInt(this.dataset.vote);
            const contentTypeId = type === 'question' ? window.questionContentType : window.answerContentType;
            
            try {
                const response = await fetch('/syringly/vote/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `content_type_id=${contentTypeId}&object_id=${id}&value=${vote}`
                });
                const data = await response.json();
                
                if (data.success) {
                    // Update UI
                    const voteCell = this.closest('.vote-cell');
                    voteCell.querySelector('.vote-count').textContent = data.new_votes;
                    
                    // Track in cookie
                    if (data.new_votes === 0) {
                        VoteTracker.removeVote(contentType, id);
                        this.classList.remove('voted-up', 'voted-down');
                    } else {
                        VoteTracker.recordVote(contentType, id, data.new_votes);
                        this.classList.add(vote === 1 ? 'voted-up' : 'voted-down');
                        this.classList.remove(vote === 1 ? 'voted-down' : 'voted-up');
                    }
                }
            } catch (error) {
                console.error('Vote error:', error);
            }
        });
    });
}

// Helper to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
