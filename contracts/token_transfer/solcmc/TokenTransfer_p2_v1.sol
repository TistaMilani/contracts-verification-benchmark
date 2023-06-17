// SPDX-License-Identifier: UNLICENSED
pragma solidity >= 0.8.2;

import "./lib/IERC20.sol";

contract TokenTransfer {

    IERC20 token;
    bool ever_deposited;

    // ghost variables
    uint _count_deposit;

    // v1
    constructor(IERC20 token_) {
        token = token_;
    }

    // v1
    function deposit() external {
        require(!ever_deposited);

        ever_deposited = true;
        uint allowance = token.allowance(msg.sender, address(this));
        token.transferFrom(msg.sender, address(this), allowance);

        _count_deposit += 1;	
    }

    // v1
    function withdraw(uint amount) external {
        token.transfer(msg.sender, amount);
    }

    // p2
    function invariant() public view {
        assert(_count_deposit <= 1);
    }
    
}