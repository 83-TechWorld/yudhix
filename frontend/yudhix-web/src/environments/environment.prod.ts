// Production / mobile builds. Point apiUrl at the public gateway before shipping to the stores:
// a phone can't reach "localhost" on your laptop.
export const environment = {
  production: true,
  apiUrl: 'http://localhost:8000',
  tenantId: '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d',
};
