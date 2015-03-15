#include <Halide.h>
  #include <vector>
  using namespace std;
  using namespace Halide;

  int main(){ 
uint8_t * main_buf = new uint8_t[150];
for(int i=0; i < 10; i++){
	main_buf[i*15] = 0;
	main_buf[i*15+1] = 0;
	main_buf[i*15+2] = 0;
	main_buf[i*15+3] = 0;
	main_buf[i*15+4] = 0;
	main_buf[i*15+5] = 10*i;
	main_buf[i*15+6] = 10*i;
	main_buf[i*15+7] = 10*i;
	main_buf[i*15+8] = 10*i;
	main_buf[i*15+9] = 10*i;
	main_buf[i*15+10] = 10*i;
	main_buf[i*15+11] = 10*i;
	main_buf[i*15+12] = 10*i;
	main_buf[i*15+13] = 10*i;
	main_buf[i*15+14] = 10*i;
}


buffer_t * r_buf = (buffer_t *)malloc(sizeof(buffer_t));
buffer_t * g_buf = (buffer_t *)malloc(sizeof(buffer_t));
buffer_t * b_buf = (buffer_t *)malloc(sizeof(buffer_t));

r_buf->extent[0] = 10;
r_buf->extent[1] = 5;
r_buf->extent[2] = 0; r_buf->extent[3] = 0;

r_buf->stride[0] = 3;
r_buf->stride[1] = 30;
r_buf->stride[2] = 0;
r_buf->stride[3] = 0;
r_buf->min[0] = 0; r_buf->min[1] = 0; r_buf->min[2] = 0; r_buf->min[3] = 0;
r_buf->elem_size = 1;
r_buf->host = (uint8_t *)(uint32_t)main_buf;
r_buf->host_dirty = 0; r_buf->dev_dirty = 0; r_buf->dev = 0;


g_buf->extent[0] = 10;
g_buf->extent[1] = 5;
g_buf->extent[2] = 0; g_buf->extent[3] = 0;

g_buf->stride[0] = 3;
g_buf->stride[1] = 30;
g_buf->stride[2] = 0;
g_buf->stride[3] = 0;
g_buf->min[0] = 0; g_buf->min[1] = 0; g_buf->min[2] = 0; g_buf->min[3] = 0;
g_buf->elem_size = 1;
g_buf->host = (uint8_t *)((uint32_t)main_buf + 1);
g_buf->host_dirty = 0; g_buf->dev_dirty = 0; g_buf->dev = 0;



b_buf->extent[0] = 10;
b_buf->extent[1] = 5;
b_buf->extent[2] = 0; b_buf->extent[3] = 0;

b_buf->stride[0] = 3;
b_buf->stride[1] = 30;
b_buf->stride[2] = 0;
b_buf->stride[3] = 0;
b_buf->min[0] = 0; b_buf->min[1] = 0; b_buf->min[2] = 0; b_buf->min[3] = 0;
b_buf->elem_size = 1;;
b_buf->host = (uint8_t *)((uint32_t)main_buf+2);
b_buf->host_dirty = 0; b_buf->dev_dirty = 0; b_buf->dev = 0;

Var x_0;
Var x_1;
Func inter_1;
uint8_t p_1 = 25;
// Image<uint8_t> input_1 = Image(UInt(8), g_buf, name="input_1");
// Image<uint8_t> input_67 = Image(UInt(8), b_buf, name="input_67");
// Image<uint8_t> input_68 = Image(UInt(8), r_buf, name="input_68");
Buffer r = Buffer(UInt(8),r_buf);
Buffer b = Buffer(UInt(8),b_buf);
Buffer g = Buffer(UInt(8),g_buf);

ImageParam input_1(UInt(8),2);
input_1.set(g);
input_1.set_stride(0,3);
ImageParam input_67(UInt(8),2);
input_67.set(b);
input_67.set_stride(0,3);
ImageParam input_68(UInt(8),2);
input_68.set(r);
input_68.set_stride(0,3);
Expr inter_1_0_1 = (( 0  &  1 ) -  1 );
Expr inter_1_0_0 = select((cast<uint32_t>( (  ( (( 8192  + ( 1  * cast<uint32_t>( input_68(x_0,x_1) ) *  4915 ) + (cast<uint32_t>( input_1(x_0,x_1) ) *  9667 ) + (cast<uint32_t>( input_67(x_0,x_1) ) *  1802 )) >> cast<uint32_t>( 14 )) ) & 255 ) ) < cast<uint32_t>( (  ( ( p_1 ) ) & 255 ) )),((( 0  -  1 ) &  1 ) -  1 ),inter_1_0_1);
inter_1(x_0,x_1) = cast<uint8_t>( inter_1_0_0) ;


vector<Argument> args;
args.push_back(input_1);
args.push_back(input_67);
args.push_back(input_68);


inter_1.trace_stores();
// inter_1.compile_to_c("temp.cpp", args, "thresh");
Halide::Image<uint8_t> output = inter_1.realize(10, 5);

printf("Evaluating threshold\n");


return 0;
}
