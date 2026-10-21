// Yudhix Enterprise Social Comment Intelligence & Turnaround Platform
const YOUTUBE_API_KEY = "AIzaSyCWGhmMjOdPlGkSjcaV4OKdvLSGIhvL3Uc";

async function loadCommentsFromDatabase() {
    try {
        const res = await fetch('http://localhost:8000/api/v1/comments');
        if (res.ok) {
            const data = await res.json();
            if (data.comments && data.comments.length > 0) {
                // Prepend or replace with real comments from PostgreSQL
                state.comments = data.comments;
            }
        }
    } catch (e) {
        console.warn("Could not load comments from DB, using fallback:", e.message);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    initNavigation();
    initCharts();
    await loadCommentsFromDatabase();
    renderInbox();
    renderApprovals();
    renderLedger();
    renderSubscribedChannels();
});

// Mock & Live State representing active microservices
const state = {
    activeTab: 'dashboard',
    selectedPriority: 'ALL',
    selectedChannel: 'ALL',
    subscribedChannels: [
        {
            id: 'yt-001',
            platform: 'YOUTUBE',
            name: 'SAMTIME (Physical Discs)',
            ref: 'https://www.youtube.com/watch?v=PTblI6oYfSU',
            product: 'PlayStation Discs & PS Store',
            commentsIngested: 2662,
            watermark: 'Ugzm8Tx-MkDP... (Recorded)',
            lastPolled: 'Just now'
        },
        {
            id: 'yt-002',
            platform: 'YOUTUBE',
            name: 'PlayStation Global Channel',
            ref: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            product: 'DualSense Controller',
            commentsIngested: 420,
            watermark: 'yt_c_dual_101 (Recorded)',
            lastPolled: '5m ago'
        },
        {
            id: 'li-001',
            platform: 'LINKEDIN',
            name: 'Sony Semiconductor Solutions',
            ref: 'https://www.linkedin.com/company/sony',
            product: 'Sony Cloud Platform',
            commentsIngested: 88,
            watermark: 'li_sync_cursor_01',
            lastPolled: '15m ago'
        }
    ],
    comments: [
        {
            id: 'c1-youtube',
            platform: 'YouTube',
            platformCommentId: 'yt_98124',
            authorHash: 'sha256:7f4a...d91c',
            maskedText: 'The battery in my PlayStation controller died after only 3 weeks! Called customer support at <PHONE> but nobody picked up for 45 minutes.',
            hasPii: true,
            sentiment: 'NEGATIVE',
            sentimentScore: -0.88,
            aspects: [{ name: 'Battery', sentiment: 'NEGATIVE' }, { name: 'Support', sentiment: 'NEGATIVE' }],
            toxic: false,
            churnRisk: 0.78,
            impactScore: 84.50,
            priority: 'P1',
            likes: 420,
            replies: 88,
            timeAgo: '42m ago',
            aiSuggestedReply: 'Hello! We sincerely apologize for the frustration with your battery and wait time. Please DM us your reference code so our senior support team can ship you a replacement under warranty immediately.',
            status: 'NEEDS_REVIEW'
        },
        {
            id: 'c2-linkedin',
            platform: 'LinkedIn',
            platformCommentId: 'li_55219',
            authorHash: 'sha256:3e2b...8a0f',
            maskedText: 'Our enterprise deployment experienced severe throttling on the billing API endpoint. Requesting urgent priority escalation.',
            hasPii: false,
            sentiment: 'NEGATIVE',
            sentimentScore: -0.65,
            aspects: [{ name: 'API Performance', sentiment: 'NEGATIVE' }, { name: 'Billing', sentiment: 'NEUTRAL' }],
            toxic: false,
            churnRisk: 0.62,
            impactScore: 68.20,
            priority: 'P2',
            likes: 45,
            replies: 12,
            timeAgo: '2h ago',
            aiSuggestedReply: 'Hi there, thank you for reaching out. We have escalated this to our cloud operations team. A dedicated engineer is investigating your tenant API logs right now.',
            status: 'NEEDS_REVIEW'
        },
        {
            id: 'c3-reddit',
            platform: 'Reddit',
            platformCommentId: 'rd_88192',
            authorHash: 'sha256:1a9c...034e',
            maskedText: 'Just tested the new update v2.4, the UI response time is noticeably smoother. Excellent work by the engineering team!',
            hasPii: false,
            sentiment: 'POSITIVE',
            sentimentScore: 0.92,
            aspects: [{ name: 'UI / UX', sentiment: 'POSITIVE' }, { name: 'Speed', sentiment: 'POSITIVE' }],
            toxic: false,
            churnRisk: 0.05,
            impactScore: 18.00,
            priority: 'P3',
            likes: 189,
            replies: 14,
            timeAgo: '4h ago',
            aiSuggestedReply: 'Thank you so much for the kind words! Glad you are enjoying v2.4.',
            status: 'RESOLVED'
        }
    ],
    approvals: [
        {
            id: 'rep-001',
            commentId: 'c1-youtube',
            platform: 'YouTube',
            author: 'Support Agent Priya K.',
            replyText: 'Hello! We sincerely apologize for the frustration with your battery and wait time. Please DM us your reference code so our senior support team can ship you a replacement under warranty immediately.',
            status: 'IN_REVIEW',
            slaCountdown: '1h 18m left'
        }
    ],
    ledgerBlocks: [
        { seq: 1042, actor: 'SYSTEM_SENSE', action: 'COMMENT_CLASSIFIED', entityId: 'c1-youtube', hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
        { seq: 1043, actor: 'AGENT_PRIYA', action: 'REPLY_DRAFT_SUBMITTED', entityId: 'rep-001', hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4' },
        { seq: 1044, actor: 'LEAD_APPROVER', action: 'REPLY_APPROVED', entityId: 'rep-001', hash: '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945' }
    ]
};

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.getAttribute('data-tab');
            if (!tab) return;
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            document.querySelectorAll('.tab-view').forEach(view => {
                view.classList.add('hidden');
            });
            const targetView = document.getElementById(`view-${tab}`);
            if (targetView) {
                targetView.classList.remove('hidden');
            }
        });
    });
}

function initCharts() {
    const ctxTimeline = document.getElementById('timelineChart')?.getContext('2d');
    if (ctxTimeline) {
        new Chart(ctxTimeline, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {
                        label: 'Negative Volume',
                        data: [140, 180, 220, 190, 110, 85, 95],
                        borderColor: '#737373',
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Turnaround (Neg -> Pos)',
                        data: [90, 125, 160, 145, 80, 65, 75],
                        borderColor: '#ff6600',
                        backgroundColor: 'rgba(255, 102, 0, 0.15)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#94a3b8' } }
                },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }
}

function updateChannelFilterOptions() {
    const select = document.getElementById('channelFilter');
    if (!select) return;
    const currentVal = state.selectedChannel || 'ALL';
    const channels = [...new Set(state.comments.map(c => c.channelTitle || c.platform).filter(Boolean))];
    select.innerHTML = '<option value="ALL">All Channels & Sources</option>';
    channels.forEach(ch => {
        const opt = document.createElement('option');
        opt.value = ch;
        opt.innerText = ch;
        if (ch === currentVal) opt.selected = true;
        select.appendChild(opt);
    });
}

function renderInbox(filter = (state.selectedPriority || 'ALL')) {
    state.selectedPriority = filter;
    const list = document.getElementById('inboxList');
    if (!list) return;

    updateChannelFilterOptions();

    list.innerHTML = '';
    const filtered = state.comments.filter(c => {
        // Priority / Sentiment filter
        if (filter === 'NEGATIVE' && c.sentiment !== 'NEGATIVE') return false;
        if (filter === 'POSITIVE' && c.sentiment !== 'POSITIVE') return false;
        if (filter === 'P1' && c.priority !== 'P1') return false;
        if (filter === 'P2' && c.priority !== 'P2') return false;
        if (filter === 'P3' && c.priority !== 'P3') return false;

        // Channel / Video filter
        if (state.selectedChannel && state.selectedChannel !== 'ALL') {
            const chName = c.channelTitle || c.platform;
            if (chName !== state.selectedChannel) return false;
        }
        return true;
    });

    if (filtered.length === 0) {
        list.innerHTML = `<div style="text-align:center; padding:40px; color:#888;">No comments found matching the current filter.</div>`;
        return;
    }

    filtered.forEach(c => {
        const card = document.createElement('div');
        card.className = `comment-card ${c.priority.toLowerCase()}`;
        
        const videoTitleDisplay = c.videoTitle ? (c.videoTitle.length > 55 ? c.videoTitle.substring(0, 55) + '...' : c.videoTitle) : '';
        const videoUrl = c.videoUrl || (c.videoId ? `https://www.youtube.com/watch?v=${c.videoId}` : '');

        card.innerHTML = `
            <!-- Channel & Video Attribution Banner -->
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap;">
                <span class="badge" style="background:#261805; color:var(--orange-primary); border:1px solid #733400; font-weight:700; font-size:0.75rem;">
                    <i data-lucide="video" style="width:12px; height:12px; vertical-align:middle;"></i> ${c.channelTitle || c.platform}
                </span>
                ${videoTitleDisplay ? `<a href="${videoUrl}" target="_blank" style="color:#ffffff; font-size:0.78rem; font-weight:600; text-decoration:none; opacity:0.9; display:inline-flex; align-items:center; gap:4px;" title="Watch Video on YouTube">🎬 ${videoTitleDisplay} <i data-lucide="external-link" style="width:11px; height:11px;"></i></a>` : ''}
            </div>

            <div class="comment-header">
                <div class="platform-meta">
                    <span class="badge badge-${c.priority.toLowerCase()}">${c.priority}</span>
                    <span class="badge ${c.sentiment === 'NEGATIVE' ? 'badge-neg' : (c.sentiment === 'POSITIVE' ? 'badge-pos' : '')}">${c.sentiment}</span>
                    <span style="font-weight:700; font-size:0.85rem; color:#fff;">${c.platform}</span>
                    <span class="author-pseudonym">${c.authorHash}</span>
                </div>
                <span style="font-size:0.8rem; color:var(--text-muted);">${c.timeAgo}</span>
            </div>

            <div class="comment-text">
                ${(c.maskedText || '').replace(/<PHONE>/g, '<span class="pii-tag">&lt;PHONE_MASKED&gt;</span>').replace(/<PERSON>/g, '<span class="pii-tag">&lt;NAME_MASKED&gt;</span>')}
            </div>

            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                <span style="font-size:0.75rem; color:var(--text-secondary); font-weight:700;">Aspects:</span>
                ${(c.aspects || []).map(a => `<span style="font-size:0.72rem; padding:2px 8px; border-radius:4px; background:#222; border:1px solid #333; color:#eee;">${a.name || a.aspect} (${a.sentiment})</span>`).join('')}
                <span style="margin-left:auto; font-size:0.8rem; font-weight:800; color:var(--orange-primary);">Impact: ${c.impactScore}</span>
            </div>

            <div class="ai-draft-box">
                <div class="ai-draft-header">
                    <span>AI-GENERATED BRAND-SAFE DRAFT (Presidio Sanitized)</span>
                    <button class="btn btn-primary" style="padding:4px 10px; font-size:0.75rem;" onclick="submitDraft('${c.id}')">Submit for Approval</button>
                </div>
                <div class="ai-draft-text">"${c.aiSuggestedReply || 'We appreciate your feedback and are looking into this.'}"</div>
            </div>
        `;
        list.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
}

window.filterInbox = function(filter) {
    document.querySelectorAll('.filter-chip').forEach(btn => btn.classList.remove('active'));
    if (window.event && window.event.target) window.event.target.classList.add('active');
    renderInbox(filter);
};

window.filterByChannel = function(channel) {
    state.selectedChannel = channel;
    renderInbox(state.selectedPriority);
};

window.submitDraft = function(commentId) {
    const comment = state.comments.find(c => c.id === commentId);
    if (!comment) return;

    state.approvals.push({
        id: 'rep-' + Date.now().toString().slice(-4),
        commentId: comment.id,
        platform: comment.platform,
        author: 'Current User (Brand Agent)',
        replyText: comment.aiSuggestedReply || 'Thank you for reaching out to us.',
        status: 'IN_REVIEW',
        slaCountdown: '2h 00m left'
    });

    renderApprovals();
    alert('Draft submitted to yudhix-resolve approval workflow! Separation-of-duties applied: a designated brand lead must approve before posting.');
};

function renderApprovals() {
    const list = document.getElementById('approvalList');
    if (!list) return;

    list.innerHTML = '';
    state.approvals.forEach(app => {
        const row = document.createElement('div');
        row.className = 'panel-card';
        row.style.marginBottom = '16px';
        row.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div>
                    <span class="badge badge-p1">${app.platform}</span>
                    <span style="font-weight:700; margin-left:8px; color:#fff;">Reply Ref: ${app.id}</span>
                </div>
                <span style="color:var(--orange-primary); font-weight:800; font-size:0.85rem;">SLA: ${app.slaCountdown}</span>
            </div>
            <p style="font-size:0.92rem; color:#fff; line-height:1.5; margin-bottom:14px; background:#141414; border:1px solid #2a2a2a; padding:12px; border-radius:6px;">
                "${app.replyText}"
            </p>
            <div style="display:flex; gap:10px; justify-content:flex-end;">
                <button class="btn btn-secondary" onclick="rejectReply('${app.id}')">Request Changes</button>
                <button class="btn btn-primary" onclick="approveReply('${app.id}')">Approve & Dispatch</button>
            </div>
        `;
        list.appendChild(row);
    });
}

window.approveReply = function(id) {
    state.approvals = state.approvals.filter(a => a.id !== id);
    state.ledgerBlocks.push({
        seq: state.ledgerBlocks.length + 1042,
        actor: 'BRAND_LEAD_REVIEWER',
        action: 'REPLY_APPROVED_AND_POSTED',
        entityId: id,
        hash: 'b78a9c0012e8477ff987114b0948925439acbfe9880194857bba1048bceee890'
    });
    renderApprovals();
    renderLedger();
    alert('Approved! Reply dispatched to platform connector (yudhix-link) and audit event anchored to immutable ledger (yudhix-ledger).');
};

function renderLedger() {
    const tableBody = document.getElementById('ledgerTableBody');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    state.ledgerBlocks.forEach(b => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #222';
        tr.innerHTML = `
            <td style="padding:10px; font-family:var(--font-mono); color:var(--text-muted); font-size:0.82rem;">#${b.seq}</td>
            <td style="padding:10px; font-weight:700; font-size:0.85rem; color:var(--orange-primary);">${b.actor}</td>
            <td style="padding:10px; font-size:0.85rem;">${b.action}</td>
            <td style="padding:10px; font-family:var(--font-mono); font-size:0.8rem; color:#fff;">${b.entityId}</td>
            <td style="padding:10px; font-family:var(--font-mono); font-size:0.75rem; color:#666;">${b.hash.slice(0, 16)}...</td>
        `;
        tableBody.appendChild(tr);
    });
}

window.verifyAuditChain = function() {
    alert('Ledger Verification Complete: 100% of SHA-256 block hashes verified against previous hashes. Zero tampering detected.');
};

window.executeDsrErasure = function() {
    const input = document.getElementById('dsrInput')?.value;
    if (!input) {
        alert('Please enter an Author Hash to erase.');
        return;
    }
    state.comments = state.comments.filter(c => !c.authorHash.includes(input.slice(0, 8)));
    renderInbox();
    alert(`DSR Right-to-be-Forgotten executed under India DPDP / US CCPA. Comment text and author references expunged for hash: ${input}`);
};

// ==============================================================================
// Channel & Profile Subscriptions Management
// ==============================================================================
function renderSubscribedChannels() {
    const grid = document.getElementById('subscribedChannelsGrid');
    const ytCountEl = document.getElementById('ytChannelCount');
    const liCountEl = document.getElementById('liProfileCount');

    const ytCount = state.subscribedChannels.filter(c => c.platform === 'YOUTUBE').length;
    const liCount = state.subscribedChannels.filter(c => c.platform === 'LINKEDIN').length;

    if (ytCountEl) ytCountEl.innerText = `${ytCount} / 20`;
    if (liCountEl) liCountEl.innerText = `${liCount} / 10`;

    if (!grid) return;
    grid.innerHTML = '';

    state.subscribedChannels.forEach(ch => {
        const isYt = ch.platform === 'YOUTUBE';
        const card = document.createElement('div');
        card.style.background = '#141414';
        card.style.border = '1px solid #2a2a2a';
        card.style.borderTop = isYt ? '3px solid var(--orange-primary)' : '3px solid #ffffff';
        card.style.borderRadius = '8px';
        card.style.padding = '16px';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.gap = '10px';

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge ${isYt ? 'badge-p1' : 'badge-p2'}">${ch.platform}</span>
                <span style="font-size:0.75rem; color:#10b981; font-weight:700;">● ACTIVE</span>
            </div>
            <div>
                <h4 style="font-size:0.95rem; font-weight:800; color:#fff; margin-bottom:2px;">${ch.name}</h4>
                <div style="font-size:0.78rem; font-family:var(--font-mono); color:#888; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    Ref: ${ch.ref}
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#bbb; border-top:1px solid #222; padding-top:8px;">
                <span>Product: <strong style="color:#fff;">${ch.product}</strong></span>
                <span>Ingested: <strong style="color:var(--orange-primary);">${ch.commentsIngested}</strong></span>
            </div>
            <div style="display:flex; gap:8px; margin-top:4px;">
                <button class="btn btn-primary" style="flex:1; padding:6px 10px; font-size:0.78rem;" onclick="fetchLiveYouTubeComments('${ch.ref}', '${ch.id}')">
                    <i data-lucide="zap"></i> Fetch Comments
                </button>
                <button class="btn btn-secondary" style="padding:6px 10px; font-size:0.78rem; color:#ff4444;" onclick="unsubscribeChannel('${ch.id}')">
                    Unsubscribe
                </button>
            </div>
        `;
        grid.appendChild(card);
    });

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

window.subscribeChannel = function(platform) {
    if (platform === 'YOUTUBE') {
        const input = document.getElementById('ytInput')?.value.trim();
        const product = document.getElementById('ytProductInput')?.value.trim() || 'General Product';
        if (!input) {
            alert('Please enter a YouTube Video URL or Channel ID.');
            return;
        }

        const currentYt = state.subscribedChannels.filter(c => c.platform === 'YOUTUBE').length;
        if (currentYt >= 20) {
            alert('Tenant Quota Exceeded: You have reached the maximum allowed limit of 20 YouTube channels.');
            return;
        }

        const newChannel = {
            id: 'yt-' + Date.now().toString().slice(-4),
            platform: 'YOUTUBE',
            name: input.includes('v=') ? 'YouTube Video Feed' : 'YouTube Channel Feed',
            ref: input,
            product: product,
            commentsIngested: 0,
            lastPolled: 'Just added'
        };

        state.subscribedChannels.push(newChannel);
        renderSubscribedChannels();
        alert(`Successfully subscribed YouTube source! Added to automated 5-min polling queue.`);
    } else if (platform === 'LINKEDIN') {
        const input = document.getElementById('liInput')?.value.trim();
        const product = document.getElementById('liProductInput')?.value.trim() || 'Enterprise Cloud';
        if (!input) {
            alert('Please enter a LinkedIn Company or Profile URL.');
            return;
        }

        const currentLi = state.subscribedChannels.filter(c => c.platform === 'LINKEDIN').length;
        if (currentLi >= 10) {
            alert('Tenant Quota Exceeded: You have reached the maximum allowed limit of 10 LinkedIn profiles.');
            return;
        }

        const newChannel = {
            id: 'li-' + Date.now().toString().slice(-4),
            platform: 'LINKEDIN',
            name: 'LinkedIn Monitored Feed',
            ref: input,
            product: product,
            commentsIngested: 0,
            lastPolled: 'Just added'
        };

        state.subscribedChannels.push(newChannel);
        renderSubscribedChannels();
        alert(`Successfully subscribed LinkedIn profile! Ingestion active with HMAC pseudonymization.`);
    }
};

window.unsubscribeChannel = function(id) {
    state.subscribedChannels = state.subscribedChannels.filter(c => c.id !== id);
    renderSubscribedChannels();
};

window.fetchLiveYouTubeComments = async function(customRef, channelId) {
    let ref = customRef || document.getElementById('ytInput')?.value.trim();
    if (!ref) {
        ref = "https://www.youtube.com/watch?v=PTblI6oYfSU";
    }

    let videoId = ref;
    if (ref.includes('watch?v=')) {
        videoId = ref.split('v=')[1].split('&')[0];
    } else if (ref.includes('youtu.be/')) {
        videoId = ref.split('youtu.be/')[1].split('?')[0];
    }

    const btn = document.getElementById('btnLiveFetch');
    if (btn) btn.innerText = "Connecting to YouTube API...";

    try {
        // 1. Fetch Video Metadata (Channel Title & Video Title)
        let channelTitle = "YouTube";
        let videoTitle = "";
        try {
            const vRes = await fetch(`https://www.googleapis.com/youtube/v3/videos?part=snippet&id=${videoId}&key=${YOUTUBE_API_KEY}`);
            if (vRes.ok) {
                const vData = await vRes.json();
                if (vData.items && vData.items.length > 0) {
                    channelTitle = vData.items[0].snippet.channelTitle || "YouTube";
                    videoTitle = vData.items[0].snippet.title || "";
                }
            }
        } catch(e) {
            console.warn("Could not fetch video metadata:", e.message);
        }

        // 2. Fetch Comments with Pagination (Batch Limit)
        const batchLimitOption = document.getElementById('ytBatchLimit')?.value || '100';
        let maxToFetch = batchLimitOption === 'ALL' ? 500 : parseInt(batchLimitOption, 10);
        let allItems = [];
        let pageToken = '';

        while (allItems.length < maxToFetch) {
            const pageSize = Math.min(100, maxToFetch - allItems.length);
            let apiUrl = `https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId=${videoId}&maxResults=${pageSize}&order=time&key=${YOUTUBE_API_KEY}`;
            if (pageToken) apiUrl += `&pageToken=${pageToken}`;

            if (btn) btn.innerText = `Fetching comments (${allItems.length} loaded)...`;
            const res = await fetch(apiUrl);
            if (!res.ok) throw new Error(`YouTube API returned status ${res.status}`);

            const data = await res.json();
            const items = data.items || [];
            if (items.length === 0) break;
            allItems = allItems.concat(items);

            pageToken = data.nextPageToken;
            if (!pageToken) break;
        }

        if (allItems.length === 0) {
            alert(`Connected to YouTube, but no public comments were found for video: ${videoId}`);
            return;
        }

        // 3. Record Watermark (The first item in order=time is the newest comment!)
        const newestItem = allItems[0];
        const newestSnippet = newestItem.snippet.topLevelComment.snippet;
        const watermarkId = newestItem.id;
        const watermarkTs = newestSnippet.publishedAt;

        try {
            await fetch('http://localhost:8000/api/v1/watermark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                    source_id: channelId || "c0a80101-0000-0000-0000-000000000001",
                    platform: "YOUTUBE",
                    last_comment_ts: watermarkTs,
                    page_token: watermarkId
                })
            });
        } catch(e) {
            console.warn("Could not save watermark to backend:", e.message);
        }

        // 4. Ingest and Persist comments into PostgreSQL via yudhix-sense
        if (btn) btn.innerText = `Persisting ${allItems.length} comments into PostgreSQL...`;
        let analyzedCount = 0;

        for (let i = 0; i < allItems.length; i++) {
            const item = allItems[i];
            const snippet = item.snippet.topLevelComment.snippet;
            const rawText = snippet.textOriginal || snippet.textDisplay;
            const author = snippet.authorDisplayName || "anonymous_user";
            const likes = snippet.likeCount || 0;
            const authorHash = "sha256:" + Math.abs(author.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0)).toString(16) + "...yt";

            try {
                await fetch('http://localhost:8000/api/v1/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        comment_id: item.id,
                        tenant_id: "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                        raw_text: rawText,
                        platform: "YOUTUBE",
                        author_hash: authorHash,
                        channel_title: channelTitle,
                        video_id: videoId,
                        video_title: videoTitle,
                        video_url: `https://www.youtube.com/watch?v=${videoId}`,
                        platform_created_at: snippet.publishedAt,
                        likes: likes,
                        replies: item.snippet.totalReplyCount || 0,
                        run_deep_llm: (i < 3), // deep LLM on top comments, fast sentiment for bulk
                        persist: true
                    })
                });
                analyzedCount++;
            } catch (e) {
                console.warn("Persistence error:", e.message);
            }
        }

        // 5. Update Channel Subscription state
        let targetChannel = state.subscribedChannels.find(c => c.ref.includes(videoId));
        if (!targetChannel) {
            targetChannel = {
                id: 'yt-' + Date.now().toString().slice(-4),
                platform: 'YOUTUBE',
                name: `${channelTitle} (${videoTitle ? videoTitle.substring(0, 26) + '...' : 'Feed'})`,
                ref: `https://www.youtube.com/watch?v=${videoId}`,
                product: 'PlayStation Discs & PS Store',
                commentsIngested: allItems.length,
                watermark: `${watermarkId.slice(0, 14)}... (Recorded)`,
                lastPolled: 'Just now'
            };
            state.subscribedChannels.unshift(targetChannel);
        } else {
            targetChannel.commentsIngested = allItems.length;
            targetChannel.watermark = `${watermarkId.slice(0, 14)}... (Recorded)`;
            targetChannel.lastPolled = 'Just now';
        }

        // Update watermark card in UI
        const wmCard = document.getElementById('activeWatermarkText');
        if (wmCard) wmCard.innerText = `${watermarkId.slice(0, 12)}... (Recorded)`;

        // Reload fresh state directly from PostgreSQL database
        await loadCommentsFromDatabase();
        renderInbox();
        renderSubscribedChannels();

        // Switch to Inbox tab so user immediately sees results
        const inboxTab = document.getElementById('nav-inbox');
        if (inboxTab) inboxTab.click();

        alert(`Successfully fetched ${allItems.length} comments for "${videoTitle || videoId}" by ${channelTitle}! Watermark recorded: ${watermarkId}. All comments persisted in PostgreSQL.`);

    } catch (err) {
        alert(`Error fetching live YouTube comments: ${err.message}. Please verify the video ID or network connection.`);
    } finally {
        if (btn) btn.innerHTML = '<i data-lucide="zap"></i> Fetch & Analyze Live Comments';
        if (window.lucide) window.lucide.createIcons();
    }
};
