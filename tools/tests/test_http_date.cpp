// Host test for src/AWM_time_util.h (no Arduino). CI builds and runs it:
//   g++ -std=gnu++17 -Wall -Wextra -Werror tools/tests/test_http_date.cpp -o test_http_date
// Expected epochs were computed with Python's calendar.timegm().
#include "../../src/AWM_time_util.h"

#include <stdio.h>
#include <stdlib.h>

static int failures = 0;

static void expectEpoch(const char *date, long long want) {
  time_t got = 0;
  if (!AWM_parseHttpDate(date, &got)) {
    printf("FAIL: rejected \"%s\"\n", date);
    failures++;
  } else if ((long long)got != want) {
    printf("FAIL: \"%s\" -> %lld, want %lld\n", date, (long long)got, want);
    failures++;
  }
}

static void expectReject(const char *date) {
  time_t got = 0;
  if (AWM_parseHttpDate(date, &got)) {
    printf("FAIL: accepted \"%s\" -> %lld\n", date, (long long)got);
    failures++;
  }
}

static void expectTrue(bool cond, const char *what) {
  if (!cond) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

static void runDateCases() {
  expectEpoch("Sun, 06 Nov 1994 08:49:37 GMT", 784111777LL);  // RFC 7231 example
  expectEpoch("Thu, 01 Jan 1970 00:00:01 GMT", 1LL);
  expectEpoch("Tue, 29 Feb 2000 12:00:00 GMT", 951825600LL);   // 2000 is a leap year
  expectEpoch("Mon, 01 Mar 2100 00:00:00 GMT", 4107542400LL);  // 2100 is not
  expectEpoch("Tue, 19 Jan 2038 03:14:08 GMT", 2147483648LL);  // past 32-bit time_t
  expectEpoch("Sat, 03 Oct 2026 23:59:59 GMT", 1791071999LL);
  expectReject("Thu, 01 Jan 1970 00:00:00 GMT");  // epoch 0 was rejected before too
  expectReject("");
  expectReject("not a date at all, not a date at all");
  expectReject("Sun, 06 Foo 1994 08:49:37 GMT");
  expectReject("Sun, 06 anF 1994 08:49:37 GMT");  // straddles "Jan" and "Feb"
  expectReject("Sun, 32 Nov 1994 08:49:37 GMT");
  expectReject("Sun, 06 Nov 1994 24:00:00 GMT");
}

int main() {
  setenv("TZ", "UTC0", 1);
  tzset();
  runDateCases();
  setenv("TZ", "AEST-10", 1);  // the result must not depend on TZ
  tzset();
  runDateCases();

  expectTrue(!AWM_clockValid(1483228799LL), "2016-12-31 23:59:59 is not valid");
  expectTrue(AWM_clockValid(1483228800LL), "2017-01-01 00:00:00 is valid");
  expectTrue(!AWM_clockValid(100001LL), "1970-01-02 is not valid");

  if (failures) {
    printf("%d failure(s)\n", failures);
    return 1;
  }
  printf("all time util tests passed\n");
  return 0;
}
