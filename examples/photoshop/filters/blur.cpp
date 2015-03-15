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
ImageParam input_1(UInt(8),2);
Func output_2;
 output_2(x_0,x_1)  =  cast<uint8_t>(  ( (( 4  + ( 4  * cast<uint32_t>( input_1(x_0+1,x_1+1) )) + cast<uint32_t>( input_1(x_0+1,x_1) ) + cast<uint32_t>( input_1(x_0,x_1+1) ) + cast<uint32_t>( input_1(x_0+2,x_1+1) ) + cast<uint32_t>( input_1(x_0+1,x_1+2) )) >> cast<uint32_t>( 3 )) ) & 255 ) ;

 AUTOTUNE_HOOK(output_2);

 vector<Argument> args;
args.push_back(input_1);
output_2.compile_to_file("halide_out",args);
return 0;
}

