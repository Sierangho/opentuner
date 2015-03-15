#include <iostream>
#include <math.h>
#include <float.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>

extern "C" void *halide_malloc(void *ctx, size_t);
extern "C" void halide_free(void *ctx, void *ptr);
extern "C" void *halide_print(void *ctx, const void *str);
extern "C" void *halide_error(void *ctx, const void *str);
extern "C" int halide_debug_to_file(void *ctx, const char *filename, void *data, int, int, int, int, int, int);
extern "C" int halide_start_clock(void *ctx);
extern "C" int64_t halide_current_time_ns(void *ctx);
extern "C" uint64_t halide_profiling_timer(void *ctx);

#ifdef _WIN32
extern "C" float roundf(float);
extern "C" double round(double);
#else
inline float asinh_f32(float x) {return asinhf(x);}
inline float acosh_f32(float x) {return acoshf(x);}
inline float atanh_f32(float x) {return atanhf(x);}
inline double asinh_f64(double x) {return asinh(x);}
inline double acosh_f64(double x) {return acosh(x);}
inline double atanh_f64(double x) {return atanh(x);}
#endif
inline float sqrt_f32(float x) {return sqrtf(x);}
inline float sin_f32(float x) {return sinf(x);}
inline float asin_f32(float x) {return asinf(x);}
inline float cos_f32(float x) {return cosf(x);}
inline float acos_f32(float x) {return acosf(x);}
inline float tan_f32(float x) {return tanf(x);}
inline float atan_f32(float x) {return atanf(x);}
inline float sinh_f32(float x) {return sinhf(x);}
inline float cosh_f32(float x) {return coshf(x);}
inline float tanh_f32(float x) {return tanhf(x);}
inline float hypot_f32(float x, float y) {return hypotf(x, y);}
inline float exp_f32(float x) {return expf(x);}
inline float log_f32(float x) {return logf(x);}
inline float pow_f32(float x, float y) {return powf(x, y);}
inline float floor_f32(float x) {return floorf(x);}
inline float ceil_f32(float x) {return ceilf(x);}
inline float round_f32(float x) {return roundf(x);}

inline double sqrt_f64(double x) {return sqrt(x);}
inline double sin_f64(double x) {return sin(x);}
inline double asin_f64(double x) {return asin(x);}
inline double cos_f64(double x) {return cos(x);}
inline double acos_f64(double x) {return acos(x);}
inline double tan_f64(double x) {return tan(x);}
inline double atan_f64(double x) {return atan(x);}
inline double sinh_f64(double x) {return sinh(x);}
inline double cosh_f64(double x) {return cosh(x);}
inline double tanh_f64(double x) {return tanh(x);}
inline double hypot_f64(double x, double y) {return hypot(x, y);}
inline double exp_f64(double x) {return exp(x);}
inline double log_f64(double x) {return log(x);}
inline double pow_f64(double x, double y) {return pow(x, y);}
inline double floor_f64(double x) {return floor(x);}
inline double ceil_f64(double x) {return ceil(x);}
inline double round_f64(double x) {return round(x);}

inline float maxval_f32() {return FLT_MAX;}
inline float minval_f32() {return -FLT_MAX;}
inline double maxval_f64() {return DBL_MAX;}
inline double minval_f64() {return -DBL_MAX;}
inline uint8_t maxval_u8() {return 0xff;}
inline uint8_t minval_u8() {return 0;}
inline uint16_t maxval_u16() {return 0xffff;}
inline uint16_t minval_u16() {return 0;}
inline uint32_t maxval_u32() {return 0xffffffff;}
inline uint32_t minval_u32() {return 0;}
inline uint64_t maxval_u64() {return 0xffffffffffffffff;}
inline uint64_t minval_u64() {return 0;}
inline int8_t maxval_s8() {return 0x7f;}
inline int8_t minval_s8() {return 0x80;}
inline int16_t maxval_s16() {return 0x7fff;}
inline int16_t minval_s16() {return 0x8000;}
inline int32_t maxval_s32() {return 0x7fffffff;}
inline int32_t minval_s32() {return 0x80000000;}
inline int64_t maxval_s64() {return 0x7fffffffffffffff;}
inline int64_t minval_s64() {return 0x8000000000000000;}

inline int8_t abs_i8(int8_t a) {return a >= 0 ? a : -a;}
inline int16_t abs_i16(int16_t a) {return a >= 0 ? a : -a;}
inline int32_t abs_i32(int32_t a) {return a >= 0 ? a : -a;}
inline int64_t abs_i64(int64_t a) {return a >= 0 ? a : -a;}
inline float abs_f32(float a) {return fabsf(a);}
inline double abs_f64(double a) {return fabs(a);}

inline float nan_f32() {return NAN;}
inline float neg_inf_f32() {return -INFINITY;}
inline float inf_f32() {return INFINITY;}
inline bool is_nan_f32(float x) {return x != x;}
inline bool is_nan_f64(double x) {return x != x;}
inline float float_from_bits(uint32_t bits) {
 union {
  uint32_t as_uint;
  float as_float;
 } u;
 u.as_uint = bits;
 return u.as_float;
}

template<typename T> T max(T a, T b) {if (a > b) return a; return b;}
template<typename T> T min(T a, T b) {if (a < b) return a; return b;}
template<typename T> T smod(T a, T b) {T result = a % b; if (result < 0) result += b < 0 ? -b : b; return result;}
template<typename T> T sdiv(T a, T b) {T q = a / b; T r = a - q*b; int bs = b >> (8*sizeof(T) - 1); int rs = r >> (8*sizeof(T) - 1); return q - (rs & bs) + (rs & ~bs);}
template<typename A, typename B> A reinterpret(B b) {A a; memcpy(&a, &b, sizeof(a)); return a;}

#ifndef BUFFER_T_DEFINED
#define BUFFER_T_DEFINED
#include <stdint.h>
typedef struct buffer_t {
    uint64_t dev;
    uint8_t* host;
    int32_t extent[4];
    int32_t stride[4];
    int32_t min[4];
    int32_t elem_size;
    bool host_dirty;
    bool dev_dirty;
} buffer_t;
#endif
static bool halide_rewrite_buffer(buffer_t *b, int32_t elem_size,
                           int32_t min0, int32_t extent0, int32_t stride0,
                           int32_t min1, int32_t extent1, int32_t stride1,
                           int32_t min2, int32_t extent2, int32_t stride2,
                           int32_t min3, int32_t extent3, int32_t stride3) {
 b->min[0] = min0;
 b->min[1] = min1;
 b->min[2] = min2;
 b->min[3] = min3;
 b->extent[0] = extent0;
 b->extent[1] = extent1;
 b->extent[2] = extent2;
 b->extent[3] = extent3;
 b->stride[0] = stride0;
 b->stride[1] = stride1;
 b->stride[2] = stride2;
 b->stride[3] = stride3;
 return true;
}


extern "C" int thresh(buffer_t *_p0_buffer, buffer_t *_p1_buffer, buffer_t *_p2_buffer, buffer_t *_f0_buffer) {
uint8_t *_p0 = (uint8_t *)(_p0_buffer->host);
const bool _p0_host_and_dev_are_null = (_p0_buffer->host == NULL) && (_p0_buffer->dev == 0);
(void)_p0_host_and_dev_are_null;
const int32_t _p0_min_0 = _p0_buffer->min[0];
(void)_p0_min_0;
const int32_t _p0_min_1 = _p0_buffer->min[1];
(void)_p0_min_1;
const int32_t _p0_min_2 = _p0_buffer->min[2];
(void)_p0_min_2;
const int32_t _p0_min_3 = _p0_buffer->min[3];
(void)_p0_min_3;
const int32_t _p0_extent_0 = _p0_buffer->extent[0];
(void)_p0_extent_0;
const int32_t _p0_extent_1 = _p0_buffer->extent[1];
(void)_p0_extent_1;
const int32_t _p0_extent_2 = _p0_buffer->extent[2];
(void)_p0_extent_2;
const int32_t _p0_extent_3 = _p0_buffer->extent[3];
(void)_p0_extent_3;
const int32_t _p0_stride_0 = _p0_buffer->stride[0];
(void)_p0_stride_0;
const int32_t _p0_stride_1 = _p0_buffer->stride[1];
(void)_p0_stride_1;
const int32_t _p0_stride_2 = _p0_buffer->stride[2];
(void)_p0_stride_2;
const int32_t _p0_stride_3 = _p0_buffer->stride[3];
(void)_p0_stride_3;
const int32_t _p0_elem_size = _p0_buffer->elem_size;
uint8_t *_p1 = (uint8_t *)(_p1_buffer->host);
const bool _p1_host_and_dev_are_null = (_p1_buffer->host == NULL) && (_p1_buffer->dev == 0);
(void)_p1_host_and_dev_are_null;
const int32_t _p1_min_0 = _p1_buffer->min[0];
(void)_p1_min_0;
const int32_t _p1_min_1 = _p1_buffer->min[1];
(void)_p1_min_1;
const int32_t _p1_min_2 = _p1_buffer->min[2];
(void)_p1_min_2;
const int32_t _p1_min_3 = _p1_buffer->min[3];
(void)_p1_min_3;
const int32_t _p1_extent_0 = _p1_buffer->extent[0];
(void)_p1_extent_0;
const int32_t _p1_extent_1 = _p1_buffer->extent[1];
(void)_p1_extent_1;
const int32_t _p1_extent_2 = _p1_buffer->extent[2];
(void)_p1_extent_2;
const int32_t _p1_extent_3 = _p1_buffer->extent[3];
(void)_p1_extent_3;
const int32_t _p1_stride_0 = _p1_buffer->stride[0];
(void)_p1_stride_0;
const int32_t _p1_stride_1 = _p1_buffer->stride[1];
(void)_p1_stride_1;
const int32_t _p1_stride_2 = _p1_buffer->stride[2];
(void)_p1_stride_2;
const int32_t _p1_stride_3 = _p1_buffer->stride[3];
(void)_p1_stride_3;
const int32_t _p1_elem_size = _p1_buffer->elem_size;
uint8_t *_p2 = (uint8_t *)(_p2_buffer->host);
const bool _p2_host_and_dev_are_null = (_p2_buffer->host == NULL) && (_p2_buffer->dev == 0);
(void)_p2_host_and_dev_are_null;
const int32_t _p2_min_0 = _p2_buffer->min[0];
(void)_p2_min_0;
const int32_t _p2_min_1 = _p2_buffer->min[1];
(void)_p2_min_1;
const int32_t _p2_min_2 = _p2_buffer->min[2];
(void)_p2_min_2;
const int32_t _p2_min_3 = _p2_buffer->min[3];
(void)_p2_min_3;
const int32_t _p2_extent_0 = _p2_buffer->extent[0];
(void)_p2_extent_0;
const int32_t _p2_extent_1 = _p2_buffer->extent[1];
(void)_p2_extent_1;
const int32_t _p2_extent_2 = _p2_buffer->extent[2];
(void)_p2_extent_2;
const int32_t _p2_extent_3 = _p2_buffer->extent[3];
(void)_p2_extent_3;
const int32_t _p2_stride_0 = _p2_buffer->stride[0];
(void)_p2_stride_0;
const int32_t _p2_stride_1 = _p2_buffer->stride[1];
(void)_p2_stride_1;
const int32_t _p2_stride_2 = _p2_buffer->stride[2];
(void)_p2_stride_2;
const int32_t _p2_stride_3 = _p2_buffer->stride[3];
(void)_p2_stride_3;
const int32_t _p2_elem_size = _p2_buffer->elem_size;
uint8_t *_f0 = (uint8_t *)(_f0_buffer->host);
const bool _f0_host_and_dev_are_null = (_f0_buffer->host == NULL) && (_f0_buffer->dev == 0);
(void)_f0_host_and_dev_are_null;
const int32_t _f0_min_0 = _f0_buffer->min[0];
(void)_f0_min_0;
const int32_t _f0_min_1 = _f0_buffer->min[1];
(void)_f0_min_1;
const int32_t _f0_min_2 = _f0_buffer->min[2];
(void)_f0_min_2;
const int32_t _f0_min_3 = _f0_buffer->min[3];
(void)_f0_min_3;
const int32_t _f0_extent_0 = _f0_buffer->extent[0];
(void)_f0_extent_0;
const int32_t _f0_extent_1 = _f0_buffer->extent[1];
(void)_f0_extent_1;
const int32_t _f0_extent_2 = _f0_buffer->extent[2];
(void)_f0_extent_2;
const int32_t _f0_extent_3 = _f0_buffer->extent[3];
(void)_f0_extent_3;
const int32_t _f0_stride_0 = _f0_buffer->stride[0];
(void)_f0_stride_0;
const int32_t _f0_stride_1 = _f0_buffer->stride[1];
(void)_f0_stride_1;
const int32_t _f0_stride_2 = _f0_buffer->stride[2];
(void)_f0_stride_2;
const int32_t _f0_stride_3 = _f0_buffer->stride[3];
(void)_f0_stride_3;
const int32_t _f0_elem_size = _f0_buffer->elem_size;
if (_f0_host_and_dev_are_null)
{
 bool _0 = halide_rewrite_buffer(_f0_buffer, 1, _f0_min_0, _f0_extent_0, 1, _f0_min_1, _f0_extent_1, _f0_extent_0, 0, 0, 0, 0, 0, 0);
 (void)_0;
} // if _f0_host_and_dev_are_null
if (_p0_host_and_dev_are_null)
{
 bool _1 = halide_rewrite_buffer(_p0_buffer, 1, _f0_min_0, _f0_extent_0, 3, _f0_min_1, _f0_extent_1, _f0_extent_0, 0, 0, 0, 0, 0, 0);
 (void)_1;
} // if _p0_host_and_dev_are_null
if (_p1_host_and_dev_are_null)
{
 bool _2 = halide_rewrite_buffer(_p1_buffer, 1, _f0_min_0, _f0_extent_0, 3, _f0_min_1, _f0_extent_1, _f0_extent_0, 0, 0, 0, 0, 0, 0);
 (void)_2;
} // if _p1_host_and_dev_are_null
if (_p2_host_and_dev_are_null)
{
 bool _3 = halide_rewrite_buffer(_p2_buffer, 1, _f0_min_0, _f0_extent_0, 3, _f0_min_1, _f0_extent_1, _f0_extent_0, 0, 0, 0, 0, 0, 0);
 (void)_3;
} // if _p2_host_and_dev_are_null
bool _4 = _f0_host_and_dev_are_null || _p0_host_and_dev_are_null;
bool _5 = _4 || _p1_host_and_dev_are_null;
bool _6 = _5 || _p2_host_and_dev_are_null;
bool _7 = !(_6);
if (_7)
{
 bool _8 = _f0_elem_size == 1;
 if (!_8)  {
  char b3[1024];
  snprintf(b3, 1024, "%s%lld%s", "Output buffer f0 has type uint8, but elem_size of the buffer_t passed in is ", (long long)(_f0_elem_size), " instead of 1");
  void * _9 = b3;
  halide_error(NULL, _9);
  return -1;
 }
 bool _10 = _p0_elem_size == 1;
 if (!_10)  {
  char b4[1024];
  snprintf(b4, 1024, "%s%lld%s", "Input buffer p0 has type uint8, but elem_size of the buffer_t passed in is ", (long long)(_p0_elem_size), " instead of 1");
  void * _11 = b4;
  halide_error(NULL, _11);
  return -1;
 }
 bool _12 = _p1_elem_size == 1;
 if (!_12)  {
  char b5[1024];
  snprintf(b5, 1024, "%s%lld%s", "Input buffer p1 has type uint8, but elem_size of the buffer_t passed in is ", (long long)(_p1_elem_size), " instead of 1");
  void * _13 = b5;
  halide_error(NULL, _13);
  return -1;
 }
 bool _14 = _p2_elem_size == 1;
 if (!_14)  {
  char b6[1024];
  snprintf(b6, 1024, "%s%lld%s", "Input buffer p2 has type uint8, but elem_size of the buffer_t passed in is ", (long long)(_p2_elem_size), " instead of 1");
  void * _15 = b6;
  halide_error(NULL, _15);
  return -1;
 }
 bool _16 = _p0_min_0 <= _f0_min_0;
 if (!_16)  {
  char b7[1024];
  snprintf(b7, 1024, "%s%lld%s%lld%s", "Input buffer p0 is accessed at ", (long long)(_f0_min_0), ", which is before the min (", (long long)(_p0_min_0), ") in dimension 0");
  void * _17 = b7;
  halide_error(NULL, _17);
  return -1;
 }
 int32_t _18 = _f0_min_0 + _f0_extent_0;
 int32_t _19 = _18 - _p0_extent_0;
 bool _20 = _19 <= _p0_min_0;
 if (!_20)  {
  int32_t _21 = _f0_min_0 + _f0_extent_0;
  int32_t _22 = _21 + -1;
  int32_t _23 = _p0_min_0 + _p0_extent_0;
  int32_t _24 = _23 + -1;
  char b8[1024];
  snprintf(b8, 1024, "%s%lld%s%lld%s", "Input buffer p0 is accessed at ", (long long)(_22), ", which is beyond the max (", (long long)(_24), ") in dimension 0");
  void * _25 = b8;
  halide_error(NULL, _25);
  return -1;
 }
 bool _26 = _p0_min_1 <= _f0_min_1;
 if (!_26)  {
  char b9[1024];
  snprintf(b9, 1024, "%s%lld%s%lld%s", "Input buffer p0 is accessed at ", (long long)(_f0_min_1), ", which is before the min (", (long long)(_p0_min_1), ") in dimension 1");
  void * _27 = b9;
  halide_error(NULL, _27);
  return -1;
 }
 int32_t _28 = _f0_min_1 + _f0_extent_1;
 int32_t _29 = _28 - _p0_extent_1;
 bool _30 = _29 <= _p0_min_1;
 if (!_30)  {
  int32_t _31 = _f0_min_1 + _f0_extent_1;
  int32_t _32 = _31 + -1;
  int32_t _33 = _p0_min_1 + _p0_extent_1;
  int32_t _34 = _33 + -1;
  char b10[1024];
  snprintf(b10, 1024, "%s%lld%s%lld%s", "Input buffer p0 is accessed at ", (long long)(_32), ", which is beyond the max (", (long long)(_34), ") in dimension 1");
  void * _35 = b10;
  halide_error(NULL, _35);
  return -1;
 }
 bool _36 = _p1_min_0 <= _f0_min_0;
 if (!_36)  {
  char b11[1024];
  snprintf(b11, 1024, "%s%lld%s%lld%s", "Input buffer p1 is accessed at ", (long long)(_f0_min_0), ", which is before the min (", (long long)(_p1_min_0), ") in dimension 0");
  void * _37 = b11;
  halide_error(NULL, _37);
  return -1;
 }
 int32_t _38 = _f0_min_0 + _f0_extent_0;
 int32_t _39 = _38 - _p1_extent_0;
 bool _40 = _39 <= _p1_min_0;
 if (!_40)  {
  int32_t _41 = _f0_min_0 + _f0_extent_0;
  int32_t _42 = _41 + -1;
  int32_t _43 = _p1_min_0 + _p1_extent_0;
  int32_t _44 = _43 + -1;
  char b12[1024];
  snprintf(b12, 1024, "%s%lld%s%lld%s", "Input buffer p1 is accessed at ", (long long)(_42), ", which is beyond the max (", (long long)(_44), ") in dimension 0");
  void * _45 = b12;
  halide_error(NULL, _45);
  return -1;
 }
 bool _46 = _p1_min_1 <= _f0_min_1;
 if (!_46)  {
  char b13[1024];
  snprintf(b13, 1024, "%s%lld%s%lld%s", "Input buffer p1 is accessed at ", (long long)(_f0_min_1), ", which is before the min (", (long long)(_p1_min_1), ") in dimension 1");
  void * _47 = b13;
  halide_error(NULL, _47);
  return -1;
 }
 int32_t _48 = _f0_min_1 + _f0_extent_1;
 int32_t _49 = _48 - _p1_extent_1;
 bool _50 = _49 <= _p1_min_1;
 if (!_50)  {
  int32_t _51 = _f0_min_1 + _f0_extent_1;
  int32_t _52 = _51 + -1;
  int32_t _53 = _p1_min_1 + _p1_extent_1;
  int32_t _54 = _53 + -1;
  char b14[1024];
  snprintf(b14, 1024, "%s%lld%s%lld%s", "Input buffer p1 is accessed at ", (long long)(_52), ", which is beyond the max (", (long long)(_54), ") in dimension 1");
  void * _55 = b14;
  halide_error(NULL, _55);
  return -1;
 }
 bool _56 = _p2_min_0 <= _f0_min_0;
 if (!_56)  {
  char b15[1024];
  snprintf(b15, 1024, "%s%lld%s%lld%s", "Input buffer p2 is accessed at ", (long long)(_f0_min_0), ", which is before the min (", (long long)(_p2_min_0), ") in dimension 0");
  void * _57 = b15;
  halide_error(NULL, _57);
  return -1;
 }
 int32_t _58 = _f0_min_0 + _f0_extent_0;
 int32_t _59 = _58 - _p2_extent_0;
 bool _60 = _59 <= _p2_min_0;
 if (!_60)  {
  int32_t _61 = _f0_min_0 + _f0_extent_0;
  int32_t _62 = _61 + -1;
  int32_t _63 = _p2_min_0 + _p2_extent_0;
  int32_t _64 = _63 + -1;
  char b16[1024];
  snprintf(b16, 1024, "%s%lld%s%lld%s", "Input buffer p2 is accessed at ", (long long)(_62), ", which is beyond the max (", (long long)(_64), ") in dimension 0");
  void * _65 = b16;
  halide_error(NULL, _65);
  return -1;
 }
 bool _66 = _p2_min_1 <= _f0_min_1;
 if (!_66)  {
  char b17[1024];
  snprintf(b17, 1024, "%s%lld%s%lld%s", "Input buffer p2 is accessed at ", (long long)(_f0_min_1), ", which is before the min (", (long long)(_p2_min_1), ") in dimension 1");
  void * _67 = b17;
  halide_error(NULL, _67);
  return -1;
 }
 int32_t _68 = _f0_min_1 + _f0_extent_1;
 int32_t _69 = _68 - _p2_extent_1;
 bool _70 = _69 <= _p2_min_1;
 if (!_70)  {
  int32_t _71 = _f0_min_1 + _f0_extent_1;
  int32_t _72 = _71 + -1;
  int32_t _73 = _p2_min_1 + _p2_extent_1;
  int32_t _74 = _73 + -1;
  char b18[1024];
  snprintf(b18, 1024, "%s%lld%s%lld%s", "Input buffer p2 is accessed at ", (long long)(_72), ", which is beyond the max (", (long long)(_74), ") in dimension 1");
  void * _75 = b18;
  halide_error(NULL, _75);
  return -1;
 }
 bool _76 = _f0_stride_0 == 1;
 if (!_76)  {
  halide_error(NULL, "Static constraint violated: f0.stride.0 == 1");
  return -1;
 }
 bool _77 = _p0_stride_0 == 3;
 if (!_77)  {
  halide_error(NULL, "Static constraint violated: p0.stride.0 == 3");
  return -1;
 }
 bool _78 = _p1_stride_0 == 3;
 if (!_78)  {
  halide_error(NULL, "Static constraint violated: p1.stride.0 == 3");
  return -1;
 }
 bool _79 = _p2_stride_0 == 3;
 if (!_79)  {
  halide_error(NULL, "Static constraint violated: p2.stride.0 == 3");
  return -1;
 }
 int64_t _80 = (int64_t)(_f0_extent_1);
 int64_t _81 = (int64_t)(_f0_extent_0);
 int64_t _82 = _80 * _81;
 int64_t _83 = (int64_t)(_p0_extent_1);
 int64_t _84 = (int64_t)(_p0_extent_0);
 int64_t _85 = _83 * _84;
 int64_t _86 = (int64_t)(_p1_extent_1);
 int64_t _87 = (int64_t)(_p1_extent_0);
 int64_t _88 = _86 * _87;
 int64_t _89 = (int64_t)(_p2_extent_1);
 int64_t _90 = (int64_t)(_p2_extent_0);
 int64_t _91 = _89 * _90;
 int64_t _92 = (int64_t)(2147483647);
 bool _93 = _81 <= _92;
 if (!_93)  {
  halide_error(NULL, "Total allocation for buffer f0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _94 = (int64_t)(_f0_extent_1);
 int64_t _95 = (int64_t)(_f0_stride_1);
 int64_t _96 = _94 * _95;
 int64_t _97 = (int64_t)(2147483647);
 bool _98 = _96 <= _97;
 if (!_98)  {
  halide_error(NULL, "Total allocation for buffer f0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _99 = (int64_t)(2147483647);
 bool _100 = _82 <= _99;
 if (!_100)  {
  halide_error(NULL, "Product of extents for buffer f0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _101 = (int64_t)(_p0_extent_0);
 int64_t _102 = (int64_t)(3);
 int64_t _103 = _101 * _102;
 int64_t _104 = (int64_t)(2147483647);
 bool _105 = _103 <= _104;
 if (!_105)  {
  halide_error(NULL, "Total allocation for buffer p0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _106 = (int64_t)(_p0_extent_1);
 int64_t _107 = (int64_t)(_p0_stride_1);
 int64_t _108 = _106 * _107;
 int64_t _109 = (int64_t)(2147483647);
 bool _110 = _108 <= _109;
 if (!_110)  {
  halide_error(NULL, "Total allocation for buffer p0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _111 = (int64_t)(2147483647);
 bool _112 = _85 <= _111;
 if (!_112)  {
  halide_error(NULL, "Product of extents for buffer p0 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _113 = (int64_t)(_p1_extent_0);
 int64_t _114 = (int64_t)(3);
 int64_t _115 = _113 * _114;
 int64_t _116 = (int64_t)(2147483647);
 bool _117 = _115 <= _116;
 if (!_117)  {
  halide_error(NULL, "Total allocation for buffer p1 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _118 = (int64_t)(_p1_extent_1);
 int64_t _119 = (int64_t)(_p1_stride_1);
 int64_t _120 = _118 * _119;
 int64_t _121 = (int64_t)(2147483647);
 bool _122 = _120 <= _121;
 if (!_122)  {
  halide_error(NULL, "Total allocation for buffer p1 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _123 = (int64_t)(2147483647);
 bool _124 = _88 <= _123;
 if (!_124)  {
  halide_error(NULL, "Product of extents for buffer p1 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _125 = (int64_t)(_p2_extent_0);
 int64_t _126 = (int64_t)(3);
 int64_t _127 = _125 * _126;
 int64_t _128 = (int64_t)(2147483647);
 bool _129 = _127 <= _128;
 if (!_129)  {
  halide_error(NULL, "Total allocation for buffer p2 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _130 = (int64_t)(_p2_extent_1);
 int64_t _131 = (int64_t)(_p2_stride_1);
 int64_t _132 = _130 * _131;
 int64_t _133 = (int64_t)(2147483647);
 bool _134 = _132 <= _133;
 if (!_134)  {
  halide_error(NULL, "Total allocation for buffer p2 exceeds 2^31 - 1");
  return -1;
 }
 int64_t _135 = (int64_t)(2147483647);
 bool _136 = _91 <= _135;
 if (!_136)  {
  halide_error(NULL, "Product of extents for buffer p2 exceeds 2^31 - 1");
  return -1;
 }
 // produce f0
 for (int _f0_s0_v1 = _f0_min_1; _f0_s0_v1 < _f0_min_1 + _f0_extent_1; _f0_s0_v1++)
 {
  for (int _f0_s0_v0 = _f0_min_0; _f0_s0_v0 < _f0_min_0 + _f0_extent_0; _f0_s0_v0++)
  {
   int32_t _137 = _f0_s0_v1 * _f0_stride_1;
   int32_t _138 = _f0_s0_v0 + _137;
   int32_t _139 = _f0_min_1 * _f0_stride_1;
   int32_t _140 = _f0_min_0 + _139;
   int32_t _141 = _138 - _140;
   uint32_t _142 = (uint32_t)(8192);
   int32_t _143 = _f0_s0_v0 * 3;
   int32_t _144 = _f0_s0_v1 * _p2_stride_1;
   int32_t _145 = _143 + _144;
   int32_t _146 = _p2_min_0 * 3;
   int32_t _147 = _p2_min_1 * _p2_stride_1;
   int32_t _148 = _146 + _147;
   int32_t _149 = _145 - _148;
   uint8_t _150 = _p2[_149];
   uint32_t _151 = (uint32_t)(_150);
   uint32_t _152 = (uint32_t)(4915);
   uint32_t _153 = _151 * _152;
   uint32_t _154 = _142 + _153;
   int32_t _155 = _f0_s0_v1 * _p0_stride_1;
   int32_t _156 = _143 + _155;
   int32_t _157 = _p0_min_0 * 3;
   int32_t _158 = _p0_min_1 * _p0_stride_1;
   int32_t _159 = _157 + _158;
   int32_t _160 = _156 - _159;
   uint8_t _161 = _p0[_160];
   uint32_t _162 = (uint32_t)(_161);
   uint32_t _163 = (uint32_t)(9667);
   uint32_t _164 = _162 * _163;
   uint32_t _165 = _154 + _164;
   int32_t _166 = _f0_s0_v1 * _p1_stride_1;
   int32_t _167 = _143 + _166;
   int32_t _168 = _p1_min_0 * 3;
   int32_t _169 = _p1_min_1 * _p1_stride_1;
   int32_t _170 = _168 + _169;
   int32_t _171 = _167 - _170;
   uint8_t _172 = _p1[_171];
   uint32_t _173 = (uint32_t)(_172);
   uint32_t _174 = (uint32_t)(1802);
   uint32_t _175 = _173 * _174;
   uint32_t _176 = _165 + _175;
   uint32_t _177 = _176 >> 14;
   uint32_t _178 = reinterpret<uint32_t>(255);
   uint32_t _179 = _177 & _178;
   uint32_t _180 = (uint32_t)(25);
   bool _181 = _179 < _180;
   int32_t _182 = (int32_t)(_181 ? 0 : -1);
   uint8_t _183 = (uint8_t)(_182);
   _f0[_141] = _183;
  } // for _f0_s0_v0
 } // for _f0_s0_v1
 // consume f0
} // if _7
return 0;
}
