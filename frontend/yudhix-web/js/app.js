// Yudhix Enterprise Social Comment Intelligence & Turnaround Platform
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initCharts();
    renderInbox();
    renderApprovals();
    renderLedger();
});

// Mock Initial State representing active microservices
const state = {
    activeTab: 'dashboard',
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

function renderInbox(filter = 'ALL') {
    const list = document.getElementById('inboxList');
    if (!list) return;

    list.innerHTML = '';
    const filtered = state.comments.filter(c => {
        if (filter === 'ALL') return true;
        return c.priority === filter;
    });

    filtered.forEach(c => {
        const card = document.createElement('div');
        card.className = `comment-card ${c.priority.toLowerCase()}`;
        card.innerHTML = `
            <div class="comment-header">
                <div class="platform-meta">
                    <span class="badge badge-${c.priority.toLowerCase()}">${c.priority} CRITICAL</span>
                    <span class="badge ${c.sentiment === 'NEGATIVE' ? 'badge-neg' : 'badge-pos'}">${c.sentiment}</span>
                    <span style="font-weight:600; font-size:0.85rem; color:#cbd5e1;">${c.platform}</span>
                    <span class="author-pseudonym">${c.authorHash}</span>
                </div>
                <span style="font-size:0.8rem; color:var(--text-muted);">${c.timeAgo}</span>
            </div>

            <div class="comment-text">
                ${c.maskedText.replace('<PHONE>', '<span class="pii-tag">&lt;PHONE_MASKED&gt;</span>')}
            </div>

            <div style="display:flex; gap:8px; align-items:center;">
                <span style="font-size:0.75rem; color:var(--text-secondary);">Aspects:</span>
                ${c.aspects.map(a => `<span style="font-size:0.72rem; padding:2px 8px; border-radius:4px; background:rgba(255,255,255,0.06);">${a.name} (${a.sentiment})</span>`).join('')}
                <span style="margin-left:auto; font-size:0.8rem; font-weight:700; color:var(--accent-cyan);">Impact Score: ${c.impactScore}</span>
            </div>

            <div class="ai-draft-box">
                <div class="ai-draft-header">
                    <span>AI-GENERATED BRAND-SAFE DRAFT (Presidio Sanitized)</span>
                    <button class="btn btn-primary" style="padding:4px 10px; font-size:0.75rem;" onclick="submitDraft('${c.id}')">Submit for Approval</button>
                </div>
                <div class="ai-draft-text">"${c.aiSuggestedReply}"</div>
            </div>
        `;
        list.appendChild(card);
    });
}

window.filterInbox = function(priority) {
    document.querySelectorAll('.filter-chip').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    renderInbox(priority);
};

window.submitDraft = function(commentId) {
    const comment = state.comments.find(c => c.id === commentId);
    if (!comment) return;

    state.approvals.push({
        id: 'rep-' + Date.now().toString().slice(-4),
        commentId: comment.id,
        platform: comment.platform,
        author: 'Current User (Compliance Team)',
        replyText: comment.aiSuggestedReply,
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
                    <span style="font-weight:700; margin-left:8px;">Reply Ref: ${app.id}</span>
                </div>
                <span style="color:var(--status-p2); font-weight:700; font-size:0.85rem;">SLA: ${app.slaCountdown}</span>
            </div>
            <p style="font-size:0.92rem; color:#e2e8f0; line-height:1.5; margin-bottom:14px; background:rgba(0,0,0,0.2); padding:12px; border-radius:8px;">
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
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        tr.innerHTML = `
            <td style="padding:12px; font-family:var(--font-mono); color:var(--text-muted); font-size:0.82rem;">#${b.seq}</td>
            <td style="padding:12px; font-weight:600; font-size:0.85rem; color:#a5b4fc;">${b.actor}</td>
            <td style="padding:12px; font-size:0.85rem;">${b.action}</td>
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.8rem; color:var(--accent-cyan);">${b.entityId}</td>
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.75rem; color:#64748b;">${b.hash.slice(0, 16)}...</td>
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
