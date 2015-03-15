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
Func output_1;
Func output_2;
Func output_3;

 output_1(x_0,x_1)  =  cast<uint8_t>(clamp(cast<int32_t>(  ( ((((((
 	(cast<int32_t>( input_1(x_0+1,x_1+1) )
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) )
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ) 
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ) 
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ) 
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ) 
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ) 
 	+ cast<int32_t>( input_1(x_0+1,x_1+1) ))
	- cast<int32_t>( input_1(x_0+1,x_1+2) )) 
 	- cast<int32_t>( input_1(x_0+1,x_1) )) 
	- cast<int32_t>( input_1(x_0,x_1+1) )) 
 	- cast<int32_t>( input_1(x_0+2,x_1+1) ))
 	+ cast<int32_t>( 2 )) 
 	>> cast<int32_t>( 2 ))))
 	, 0, 255) )  ;


 AUTOTUNE_HOOK(output_1);

vector<Argument> args;
args.push_back(input_1);
output_1.compile_to_file("halide_out",args);
return 0;
}
