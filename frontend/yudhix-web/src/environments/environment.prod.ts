// Production / mobile builds. A phone can't reach "localhost" on your laptop: point these at
// your public API and Keycloak before shipping to the stores.
export const environment = {
  production: true,
  apiUrl: 'http://localhost:8000',
  keycloak: { url: 'http://localhost:8180', realm: 'yudhix', clientId: 'yudhix-web' },
  salesEmail: 'sales@example.com', // TODO: set your sales inbox
};
