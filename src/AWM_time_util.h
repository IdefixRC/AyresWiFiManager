// Pure time helpers for AyresWiFiManager. No Arduino or ESP-IDF types, so a
// host compiler can test them (tools/tests/test_http_date.cpp).
#ifndef AWM_TIME_UTIL_H
#define AWM_TIME_UTIL_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

// The system clock counts as valid from 2017-01-01 00:00:00 UTC: the same
// rule as Arduino's getLocalTime() ("year after 2016").
static const int64_t AWM_MIN_VALID_EPOCH = 1483228800;

static inline bool AWM_clockValid(int64_t epoch) {
  return epoch >= AWM_MIN_VALID_EPOCH;
}

// Days since 1970-01-01 for a proleptic-Gregorian date, month 1-12
// (Howard Hinnant's days_from_civil).
static inline int64_t AWM_daysFromCivil(int64_t y, int m, int d) {
  y -= m <= 2;
  const int64_t era = (y >= 0 ? y : y - 399) / 400;
  const int64_t yoe = y - era * 400;                                    // [0, 399]
  const int64_t doy = (153 * (m > 2 ? m - 3 : m + 9) + 2) / 5 + d - 1; // [0, 365]
  const int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;           // [0, 146096]
  return era * 146097 + doe - 719468;
}

// Parses an HTTP Date header ("Sun, 06 Nov 1994 08:49:37 GMT", always GMT)
// to a UTC epoch, whatever TZ is set. Returns false for malformed input,
// out-of-range fields, epoch 0 or earlier, and dates that don't fit time_t
// (32-bit on Arduino-ESP32 core 2.x).
static inline bool AWM_parseHttpDate(const char *date, time_t *outEpoch) {
  if (!date || !outEpoch || strlen(date) < 29)
    return false;
  char wdy[4] = {0}, mon[4] = {0}, tz[4] = {0};
  int d = 0, y = 0, H = 0, M = 0, S = 0;
  if (sscanf(date, "%3s, %d %3s %d %d:%d:%d %3s", wdy, &d, mon, &y, &H, &M, &S,
             tz) != 8)
    return false;

  static const char *const kMonths = "JanFebMarAprMayJunJulAugSepOctNovDec";
  const char *p = strstr(kMonths, mon);
  if (!p || strlen(mon) != 3 || (p - kMonths) % 3 != 0)
    return false;
  const int month = (int)((p - kMonths) / 3) + 1;
  if (d < 1 || d > 31 || H < 0 || H > 23 || M < 0 || M > 59 || S < 0 || S > 60)
    return false;

  const int64_t epoch =
      AWM_daysFromCivil(y, month, d) * 86400 + H * 3600 + M * 60 + S;
  if (epoch <= 0 || (int64_t)(time_t)epoch != epoch)
    return false;
  *outEpoch = (time_t)epoch;
  return true;
}

#endif // AWM_TIME_UTIL_H
