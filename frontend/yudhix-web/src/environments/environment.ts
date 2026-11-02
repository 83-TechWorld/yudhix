// Development: API (services/yudhix-sense) on :8000, Keycloak on :8180.
export const environment: { production: boolean; apiUrl: string; keycloak: { url: string; realm: string; clientId: string }; salesEmail: string } = {
  production: false,
  apiUrl: 'http://localhost:8000',
  keycloak: { url: 'http://localhost:8180', realm: 'yudhix', clientId: 'yudhix-web' },
  salesEmail: 'sales@example.com', // TODO: set your sales inbox
};
