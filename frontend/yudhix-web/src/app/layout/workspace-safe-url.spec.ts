import { workspaceSafeUrl } from './shell.component';

describe('workspaceSafeUrl', () => {
  it('drops IDs and filters that belong to the previous workspace', () => {
    expect(workspaceSafeUrl('/products/a0ee-1')).toBe('/products');
    expect(workspaceSafeUrl('/videos/PTblI6oYfSU?tab=impact')).toBe('/videos');
    expect(workspaceSafeUrl('/inbox?video=PTblI6oYfSU&comment=x')).toBe('/inbox');
    expect(workspaceSafeUrl('/ideas?idea=123')).toBe('/ideas');
    expect(workspaceSafeUrl('/settings/billing/invoices/9')).toBe('/settings/billing');
    expect(workspaceSafeUrl('/settings/ai')).toBe('/settings/ai');
    expect(workspaceSafeUrl('/analyze')).toBe('/analyze');
  });
});
