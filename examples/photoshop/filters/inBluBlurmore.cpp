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
Func inv;
Func blur;
Func sharpenmore;
// Func blurmore;
 blur(x_0,x_1)  =  cast<uint8_t>(  ( (( 4  + 
 								( 4  * cast<uint32_t>( input_1(x_0+2,x_1+2) )) 
 								+ cast<uint32_t>( input_1(x_0+2,x_1+1) ) 
 								+ cast<uint32_t>( input_1(x_0+1,x_1+2) ) 
 								+ cast<uint32_t>( input_1(x_0+3,x_1+2) ) 
 								+ cast<uint32_t>( input_1(x_0+2,x_1+3) )) 
 								>> cast<uint32_t>( 3 )) ) & 255 ) ;
 inv(x_0,x_1)  =  ~(blur(x_0,x_1)) ;
 sharpenmore(x_0,x_1)  =  cast<uint8_t>(clamp(  ( (((((((
 	(( 2  * cast<int32_t>( inv(x_0,x_1) ))
 	+ ( 2  * cast<int32_t>( inv(x_0,x_1) ))
 	+ ( 2  * cast<int32_t>( inv(x_0,x_1) )) 
 	+ ( 2  * cast<int32_t>( inv(x_0,x_1) )) 
 	+ cast<int32_t>( inv(x_0,x_1) ) 
 	+ cast<int32_t>( inv(x_0,x_1) ) 
 	+ cast<int32_t>( inv(x_0,x_1) ) 
 	+ cast<int32_t>( inv(x_0,x_1) )) 
 	- (cast<int32_t>( inv(x_0,x_1-1) ) + cast<int32_t>( inv(x_0,x_1+1) ))) 
 	 - cast<int32_t>( inv(x_0-1,x_1) ))
 	  - cast<int32_t>( inv(x_0+1,x_1) ))
 	   - (cast<int32_t>( inv(x_0-1,x_1-1) ) + cast<int32_t>( inv(x_0-1,x_1+1) )))
 	    - (cast<int32_t>( inv(x_0+1,x_1-1) ) + cast<int32_t>( inv(x_0+1,x_1+1) ))) 
 		+ cast<int32_t>( 2 )) >> cast<int32_t>( 2 )) ) ,0,255)) ;

 
 // blurmore(x_0,x_1)  =  cast<uint8_t>(  ( 
 // 	((
 // 		((( 7  + 
 // 		( 2  * (cast<uint32_t>( blur(x_0,x_1-1) ) 
 // 				+ cast<uint32_t>( blur(x_0-1,x_1) ) 
 // 				+ cast<uint32_t>( blur(x_0,x_1) ) 
 // 				+ cast<uint32_t>( blur(x_0+1,x_1) ) 
 // 				+ cast<uint32_t>( blur(x_0+0,x_1+1) )))
 // 		 + cast<uint32_t>( blur(x_0-1,x_1-1) ) 
 // 		 + cast<uint32_t>( blur(x_0+1,x_1-1) ) 
 // 		 + cast<uint32_t>( blur(x_0-1,x_1+1) ) 
 // 		 + cast<uint32_t>( blur(x_0+1,x_1+1) ))
 // 		 -  ( (cast<uint64_t>( 613566757 ) * cast<uint64_t>(( 7  + ( 2  * (cast<uint32_t>( blur(x_0+0,x_1-1) ) + cast<uint32_t>( blur(x_0-1,x_1) ) + cast<uint32_t>( blur(x_0,x_1) ) + cast<uint32_t>( blur(x_0+1,x_1) ) + cast<uint32_t>( blur(x_0,x_1+1) ))) + cast<uint32_t>( blur(x_0-1,x_1-1) ) + cast<uint32_t>( blur(x_0+1,x_1-1) ) + cast<uint32_t>( blur(x_0-1,x_1+1) ) + cast<uint32_t>( blur(x_0+1,x_1+1) )))) )
 // 		  >> ( 32)) >> cast<uint32_t>( 1 )) 
 // 	+  ( (cast<uint64_t>( 613566757 ) * cast<uint64_t>(( 7  + ( 2  * (cast<uint32_t>( blur(x_0,x_1-1) ) + cast<uint32_t>( blur(x_0-1,x_1+0) ) + cast<uint32_t>( blur(x_0,x_1) ) + cast<uint32_t>( blur(x_0+1,x_1) ) + cast<uint32_t>( blur(x_0,x_1+1) ))) + cast<uint32_t>( blur(x_0+1,x_1+1) ) + cast<uint32_t>( blur(x_0+1,x_1-1) ) + cast<uint32_t>( blur(x_0-1,x_1+1) ) + cast<uint32_t>( blur(x_0+1,x_1+1) )))) )
 // 	 >> ( 32)) >> cast<uint32_t>( 3 )) ) & 255 ) ;

AUTOTUNE_HOOK(sharpenmore);
 
vector<Argument> args;
args.push_back(input_1);
blurmore.compile_to_file("halide_out",args);
return 0;
}
