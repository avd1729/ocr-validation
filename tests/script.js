import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '10s',
};

const pdfFile = open('docs/sample.pdf', 'b');

export default function () {
  const url = 'https://g82p2ksxoe.execute-api.us-east-1.amazonaws.com/test/validate';

  const formData = {
    file: http.file(pdfFile, 'sample.pdf'),
  };

  const res = http.post(url, formData);

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
