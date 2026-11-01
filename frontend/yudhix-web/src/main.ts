import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { initNative } from './app/core/native';

bootstrapApplication(App, appConfig)
  .then(() => initNative())
  .catch((err) => console.error(err));
