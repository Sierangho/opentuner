#ifndef _HALIDE_EXALGO_H
#define _HALIDE_EXALGO_H

void do_blur_test_run(unsigned int width, unsigned int height);


void do_blur_test(unsigned int input_width,
	unsigned int input_height,
	unsigned int output_width,
	unsigned int output_height,
	unsigned int input_stride,
	unsigned int output_stride,

	unsigned int input_image,
	unsigned int output_image,
	int iter);

void do_func_test(unsigned int width, unsigned int height, unsigned int input_image, unsigned int output_image);
void do_nothing_halide();

#endif