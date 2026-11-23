// jest-dom adds custom matchers like expect(el).toBeInTheDocument()
import '@testing-library/jest-dom';

// React Router v7 uses TextEncoder, which the older jsdom bundled
// with Create React App's Jest doesn't provide. Borrow Node's.
import { TextEncoder, TextDecoder } from 'util';
Object.assign(global, { TextEncoder, TextDecoder });
