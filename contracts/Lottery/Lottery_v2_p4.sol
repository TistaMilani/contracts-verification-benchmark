// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.18;

contract Lottery {
    address immutable private manager;
    address[] private players;
    mapping (address => bool) hasEntered;

    // ghost variables
    address _winner;

    constructor() {
        manager = msg.sender;
    }

    function enter() public payable {
        require(msg.value == .01 ether);
        require(!hasEntered[msg.sender]);
        
        hasEntered[msg.sender] = true;
        players.push(msg.sender);
    }

    function random() private view returns (uint) {
        return uint(keccak256(abi.encode(block.prevrandao)));
    }

    function pickWinner(address _player) public {
        require(msg.sender == manager);

        address winner = players[random() % players.length];

        // !_isPlayer[_player] => winner != _player
        assert(hasEntered[_player] || winner != _player);
        
        for (uint i = 0; i < players.length; i++) {
            hasEntered[players[i]] = false;
        }

        players = new address[](0);

        (bool success,) = winner.call{value: address(this).balance}("");
        require(success);
    }

    function invariant() public payable {
        require(msg.value == .01 ether);

        enter();

        assert(players[players.length-1] == msg.sender);
    }

}