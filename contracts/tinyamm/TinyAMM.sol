// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import "./lib/IERC20.sol";

contract HTLC {
    IERC20 public immutable t0;
    IERC20 public immutable t1;

    uint public r0;
    uint public r1;

    bool ever_deposited;
    uint public supply;
    mapping(address => uint) public minted;
      
    constructor(address t0_, address t1_) {
	t0 = IERC20(t0_);
	t1 = IERC20(t1_);
    }

    function deposit(uint x0, uint x1) public {
	require (x0>0 && x1>0);
	
	t0.transferFrom(msg.sender, address(this), x0);
	t1.transferFrom(msg.sender, address(this), x1);
       
	uint toMint;
       
	if (ever_deposited) {
	    require(r0 * x1 == r1 * x0, "Dep precondition");
	    toMint = (x0 * supply) / r0;
	}
	else {
	    ever_deposited = true;
	    toMint = x0;
	}
       
	require(toMint > 0, "Dep precondition");
       
	minted[msg.sender] += toMint;
	supply += toMint;
	r0 += x0;
	r1 += x1;
       
	require(t0.balanceOf(address(this)) == r0);
	require(t1.balanceOf(address(this)) == r1);
    }

    function redeeem(uint x) public {
	require (minted[msg.sender] >= x);
	require (x < supply);

	uint x0 = (x * r0) / supply;
	uint x1 = (x * r1) / supply;
		
	t0.transferFrom(address(this), msg.sender, x0);
	t1.transferFrom(address(this), msg.sender, x1);

	r0 -= x0;
	r1 -= x1;
	supply -= x;
	minted[msg.sender] -= x;
	
	require(t0.balanceOf(address(this)) == r0);
	require(t1.balanceOf(address(this)) == r1);	
    }

    function swap(address t, uint x_in) public {
	require(t == address(t0) || t == address(t1));
        require(x_in > 0);
	
        bool is_t0 = t == address(t0);
        (IERC20 t_in, IERC20 t_out, uint r_in, uint r_out) = is_t0
            ? (t0, t1, r0, r1)
            : (t1, t0, r1, r0);
	
        t_in.transferFrom(msg.sender, address(this), x_in);
	
	uint x_out = x_in * r_out * (r_in + x_in);
	
        t_out.transfer(msg.sender, x_out);
	
	(r0,r1) = is_t0
	    ? (r0 + x_in, r1 - x_out)
	    : (r0 - x_out, r1 + x_in);
	
	require(t0.balanceOf(address(this)) == r0);
	require(t1.balanceOf(address(this)) == r1);
    }
    
    function invariant() public view {
	// strangely, this gives a violation:
	// require (ever_deposited);
	// assert (r0>0 && r1>0);
	
	assert (!ever_deposited || (r0>0 && r1>0));
	assert (!ever_deposited || supply > 0);
    }
   
    /* function withdraw(uint amount) external { */
    /*     require (amount <= token.balanceOf(address(this))); */
    /*     _sent += amount; */
    /*     token.transfer(msg.sender, amount); */
    /* } */  
}
