import json
from assistant.rewards.aws_utils import upload
from assistant.rewards.rewards_checker import verify_rewards
from scripts.rewards.rewards_utils import get_last_proposed_cycle, get_last_published_cycle
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger

from assistant.rewards.rewards_assistant import content_hash_to_filename, fetchCurrentMerkleData, fetchPendingMerkleData, fetch_current_rewards_tree, run_action

console = Console()

def hash(value):
    return web3.toHex(web3.keccak(text=value))

def approve_root(badger: BadgerSystem):
    badgerTree = badger.badgerTree
    if not badgerTree.hasPendingRoot():
        console.print("No pending root")
        return False
    
    current = fetchCurrentMerkleData(badger)
    pending = fetchPendingMerkleData(badger)

    (publishedRewards, sb, eb) = get_last_published_cycle(badger)
    (proposedRewards, startBlock, endBlock) = get_last_proposed_cycle(badger)

    console.print(proposedRewards["merkleRoot"])

    rootHash = hash(proposedRewards["merkleRoot"])
    contentFileName = content_hash_to_filename(rootHash)
    print("Uploading to file " + contentFileName)

    with open(contentFileName, "w") as outfile:
        json.dump(proposedRewards, outfile,indent=4)

    with open(contentFileName) as f:
        after_file = json.load(f)

    console.print(contentFileName)

    print(
        proposedRewards["merkleRoot"],
        startBlock,
        endBlock,
        badgerTree.lastProposeStartBlock(),
        badgerTree.lastProposeEndBlock(),
    )


    verify_rewards(
        badger,
        startBlock,
        endBlock,
        publishedRewards,
        proposedRewards
    )

    upload(contentFileName)

    badgerTree.approveRoot(
            proposedRewards["merkleRoot"],
            pending["contentHash"],
            proposedRewards["cycle"],
            startBlock,
            endBlock,
            {"from": badger.guardian},
        )   


    # (currentRewards, startBlock, endBlock) = get_last_proposed_cycle(badger)
    # rootApproved = run_action(
    #     badger,
    #     {
    #         "action": "guardian",
    #         "startBlock": startBlock,
    #         "endBlock": endBlock,
    #         "pastRewards": currentRewards,
    #     },
    #     test=False,
    # )

def main():
    badger = connect_badger(load_guardian=True)
    

    # If there is a pending root, approve after independently verifying it
    while True:
        try:
            approve_root(badger)
        except Exception as e:
            console.print("[red]Error[/red]", e)
        finally:
            time.sleep(10 * 60)