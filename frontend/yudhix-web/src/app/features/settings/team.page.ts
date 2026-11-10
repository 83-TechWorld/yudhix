import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, errorMessage } from '../../core/api.service';
import { Invitation, Member, WorkspaceRole } from '../../core/models';
import { ROLE_INFO, SessionService, initials } from '../../core/session.service';
import { IconComponent } from '../../shared/icon.component';
import { AgoPipe, EmptyStateComponent, ToastService } from '../../shared/ui';

@Component({
  selector: 'y-team',
  imports: [FormsModule, IconComponent, AgoPipe, EmptyStateComponent],
  template: `
    <div class="stack-lg">
      @if (canManage()) {
        <section class="card card-pad stack enter">
          <div>
            <h2>Invite people</h2>
            <p class="muted">They'll get an email with a link to join. Pending invites count towards your plan's seats.</p>
          </div>
          <form class="invite" (ngSubmit)="invite()">
            <div class="field grow">
              <label for="emails">Email addresses</label>
              <input id="emails" name="emails" class="input" [(ngModel)]="emails" placeholder="ana@brand.com, raj@agency.com" autocomplete="off" />
            </div>
            <div class="field">
              <label for="role">Role</label>
              <select id="role" name="role" class="select input" [(ngModel)]="role">
                @for (r of roles; track r) { <option [value]="r">{{ roleInfo[r].label }}</option> }
              </select>
            </div>
            <button class="btn btn-primary" type="submit" [disabled]="inviting()"><y-icon name="send" [size]="16" /> {{ inviting() ? 'Sending…' : 'Send invites' }}</button>
          </form>
          <p class="hint">{{ roleInfo[role].label }}: {{ roleInfo[role].description }}</p>
          @if (links().length) {
            <div class="links stack enter-fade">
              @for (l of links(); track l.email) {
                <div class="link-row">
                  <span class="truncate"><strong>{{ l.email }}</strong> · {{ l.sent ? 'email sent' : 'email not sent, share the link' }}</span>
                  <button class="btn btn-sm" type="button" (click)="copy(l.link)"><y-icon name="copy" [size]="14" /> Copy link</button>
                </div>
              }
            </div>
          }
        </section>
      }

      <section class="card enter" style="--i: 1">
        <div class="card-head"><h2>Members</h2><span class="subtle">{{ members()?.length ?? 0 }}</span></div>
        @if (members() === null) {
          <div class="card-body stack">@for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height: 52px"></div> }</div>
        } @else {
          <div class="list">
            @for (m of members(); track m.userId) {
              <div class="list-item member">
                <span class="avatar">{{ initials(m.name) }}</span>
                <div class="who">
                  <strong class="truncate">{{ m.name }}@if (m.userId === session.user()?.id) { <span class="subtle"> (you)</span> }</strong>
                  <span class="subtle truncate">{{ m.email }} · joined {{ m.joinedAt | ago }}</span>
                </div>
                @if (canManage() && m.userId !== session.user()?.id) {
                  <select class="select role-select" [ngModel]="m.role" (ngModelChange)="setRole(m, $event)" [attr.aria-label]="'Role for ' + m.name">
                    @for (r of roles; track r) { <option [value]="r">{{ roleInfo[r].label }}</option> }
                  </select>
                  <button class="btn btn-ghost btn-icon btn-sm" type="button" (click)="remove(m)" [attr.aria-label]="'Remove ' + m.name"><y-icon name="trash" [size]="16" /></button>
                } @else {
                  <span class="chip" [class.chip-brand]="m.role === 'admin'">{{ roleInfo[m.role].label }}</span>
                }
              </div>
            }
          </div>
        }
      </section>

      @if (canManage()) {
        <section class="card enter" style="--i: 2">
          <div class="card-head"><h2>Pending invitations</h2><span class="subtle">{{ invitations().length }}</span></div>
          <div class="list">
            @for (i of invitations(); track i.id) {
              <div class="list-item member">
                <span class="avatar pending"><y-icon name="mail" [size]="16" /></span>
                <div class="who">
                  <strong class="truncate">{{ i.email }}</strong>
                  <span class="subtle">{{ roleInfo[i.role].label }} · @if (i.expired) { <span class="expired">expired</span> } @else { invited {{ i.createdAt | ago }} }</span>
                </div>
                <button class="btn btn-sm" type="button" (click)="resend(i)">Resend</button>
                <button class="btn btn-ghost btn-icon btn-sm" type="button" (click)="revoke(i)" [attr.aria-label]="'Revoke invite for ' + i.email"><y-icon name="x" [size]="16" /></button>
              </div>
            } @empty {
              <y-empty icon="userPlus" title="No pending invitations" text="Invite teammates or client stakeholders above." />
            }
          </div>
        </section>
      }

      <section class="card card-pad enter" style="--i: 3">
        <h2>Roles</h2>
        <dl class="roles">
          @for (r of roles; track r) { <div><dt>{{ roleInfo[r].label }}</dt><dd>{{ roleInfo[r].description }}</dd></div> }
        </dl>
      </section>
    </div>
  `,
  styles: `
    .invite { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
    .invite .grow { flex: 1 1 260px; }
    .invite select { min-width: 150px; padding: 0 12px; }
    .links { background: var(--surface-2); border-radius: 12px; padding: 10px 12px; }
    .link-row { display: flex; gap: 10px; align-items: center; justify-content: space-between; font-size: 14px; }
    .member { align-items: center; }
    .who { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .avatar { width: 36px; height: 36px; border-radius: 50%; flex: none; display: grid; place-items: center; background: var(--info-soft); color: var(--info-text); font-weight: 700; font-size: 13px; }
    .avatar.pending { background: var(--surface-2); color: var(--text-3); }
    .role-select { width: auto; height: 34px; padding: 0 8px; font-size: 13.5px; }
    .expired { color: var(--danger-text); font-weight: 600; }
    .roles { display: grid; gap: 12px; margin: 12px 0 0; }
    .roles div { display: grid; grid-template-columns: 110px 1fr; gap: 12px; }
    .roles dt { font-weight: 650; }
    .roles dd { margin: 0; color: var(--text-2); }
    @media (max-width: 520px) { .roles div { grid-template-columns: 1fr; gap: 2px; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TeamPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected session = inject(SessionService);
  protected readonly roleInfo = ROLE_INFO;
  protected readonly roles: WorkspaceRole[] = ['admin', 'approver', 'agent', 'analyst'];
  protected readonly initials = initials;

  protected readonly members = signal<Member[] | null>(null);
  protected readonly invitations = signal<Invitation[]>([]);
  protected readonly canManage = signal(false);
  protected readonly inviting = signal(false);
  protected readonly links = signal<{ email: string; link: string; sent: boolean }[]>([]);
  protected emails = '';
  protected role: WorkspaceRole = 'agent';
  protected readonly adminCount = computed(() => (this.members() ?? []).filter((m) => m.role === 'admin').length);

  constructor() {
    this.load();
  }

  private load(): void {
    this.api.team().subscribe({
      next: (t) => {
        this.members.set(t.members);
        this.invitations.set(t.invitations);
        this.canManage.set(t.canManage);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected invite(): void {
    const list = this.emails.split(/[\s,;]+/).map((e) => e.trim()).filter(Boolean);
    if (!list.length) return this.toast.error('Add at least one email address.');
    this.inviting.set(true);
    this.api.invite(list, this.role).subscribe({
      next: (r) => {
        this.inviting.set(false);
        const ok = r.results.filter((x) => x.ok);
        const failed = r.results.filter((x) => !x.ok);
        this.links.set(ok.map((x) => ({ email: x.email, link: x.invitation!.link!, sent: !!x.invitation!.emailSent })));
        if (ok.length) this.toast.show(`Invited ${ok.length} ${ok.length === 1 ? 'person' : 'people'}.`);
        failed.forEach((f) => this.toast.error(`${f.email}: ${f.error}`));
        this.emails = failed.map((f) => f.email).join(', ');
        this.load();
      },
      error: (e) => {
        this.inviting.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }

  protected setRole(m: Member, role: WorkspaceRole): void {
    this.api.setRole(m.userId, role).subscribe({
      next: (r) => {
        this.members.set(r.members);
        this.toast.show(`${m.name} is now ${ROLE_INFO[role].label}.`);
      },
      error: (e) => {
        this.toast.error(errorMessage(e));
        this.load();
      },
    });
  }

  protected remove(m: Member): void {
    if (!confirm(`Remove ${m.name} from this workspace?`)) return;
    this.api.removeMember(m.userId).subscribe({
      next: (r) => {
        this.members.set(r.members);
        this.toast.show(`${m.name} was removed.`);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected resend(i: Invitation): void {
    this.api.resendInvite(i.id).subscribe({
      next: (inv) => {
        this.links.set([{ email: inv.email, link: inv.link!, sent: !!inv.emailSent }]);
        this.toast.show(inv.emailSent ? `Sent a new invite to ${inv.email}.` : 'New link created. Email failed; share the link.');
        this.load();
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected revoke(i: Invitation): void {
    this.api.revokeInvite(i.id).subscribe({
      next: () => {
        this.toast.show(`Invitation for ${i.email} revoked.`);
        this.load();
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  protected async copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      this.toast.show('Invite link copied.');
    } catch {
      this.toast.error("Couldn't copy. Select the link manually.");
    }
  }
}
