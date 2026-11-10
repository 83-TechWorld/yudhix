# yudhix-web

Angular 20 PWA for Yudhix: web, tablet and phone, packaged for iOS and Android with Capacitor 8.

```bash
npm install
npm start              # http://localhost:4200 (needs yudhix-sense on :8000)
npm test               # unit tests in headless Chrome
npm run build          # production build → dist/yudhix-web/browser
npm run mobile:sync    # build + copy into the native projects (after `npx cap add ios|android`)
```

The API address and tenant live in `src/environments/`. See the root [README](../../README.md) (sections 4.1, 7, 8 and 12) for the product flow, folder layout, configuration and API.
