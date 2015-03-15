#include <Halide.h>
  #include <vector>
  using namespace std;
  using namespace Halide;


#ifndef AUTOTUNE_HOOK
#define AUTOTUNE_HOOK(x)
#endif

  int main(){ 

Var x_0;
Var x_1;
Func inter_1;
Param<uint8_t> p_1;
ImageParam input_1(UInt(8),2);
input_1.set_stride(0,3);
ImageParam input_67(UInt(8),2);
input_67.set_stride(0,3);
ImageParam input_68(UInt(8),2);
input_68.set_stride(0,3);
Expr inter_1_0_1 = (( 0  &  1 ) -  1 );
Expr inter_1_0_0 = select((cast<uint32_t>( (  ( (( 8192  + ( 1  * cast<uint32_t>( input_68(x_0,x_1) ) *  4915 ) + (cast<uint32_t>( input_1(x_0,x_1) ) *  9667 ) + (cast<uint32_t>( input_67(x_0,x_1) ) *  1802 )) >> cast<uint32_t>( 14 )) ) & 255 ) ) < cast<uint32_t>( (  ( ( p_1 ) ) & 255 ) )),((( 0  -  1 ) &  1 ) -  1 ),inter_1_0_1);
inter_1(x_0,x_1) = cast<uint8_t>( inter_1_0_0) ;
inter_1.output_buffer().set_stride(0,3);

AUTOTUNE_HOOK(inter_1);

vector<Argument> args;
args.push_back(p_1);
args.push_back(input_1);
args.push_back(input_67);
args.push_back(input_68);

inter_1.compile_to_assembly("halide_out",args);
return 0;
}
