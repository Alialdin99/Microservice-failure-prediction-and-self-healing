import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  stages: [
    { duration: '5m', target: 100 }, // traffic ramp-up from 1 to 100 users over 5 minutes
    { duration: '30m', target: 100 }, // stay at 100 users for 30 minutes
    { duration: '5m', target: 0 },    // ramp-down to 0 users
  ],
};

export default function () {
  http.get('http://nginx.default.svc.cluster.local:80/');
  sleep(1);
}
