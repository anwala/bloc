import unittest

from ubs.MarkovChain import UBSMarkovChain
from ubs.util import getDictFromJsonGZ


class TestMCStateless(unittest.TestCase):
    sequence_lst = [
        "r⚂r⚁r⚁r",
        "⚂r",
        "p⚂r",
        "⚀r",
        "⚁r",
        "⚂r⚂r⚁r⚁r⚀r⚁r",
        "⚂r⚁r⚁r⚁r⚁r⚁r⚁p⚁r⚁r",
        "⚂r⚁r⚁p⚀r⚁r⚁r⚁r⚁r⚁p⚂p",
        "⚂r⚂r⚁ρρTρρ⚁r⚁r⚀p⚁p⚁r⚁rr",
        "⚂r⚂r⚁r⚁r⚂p",
    ]

    unknown_seq = "ρρTρρ⚁r⚁r⚀p⚁p⚁r⚁rr"
    model_file = "./sample_markov_chain_model/ubs_mk_model.json.gz"

    def test_use_case_1(self):
        """
        train model from list of UBS sequences (sequence_lst), save the model to a file (model_file)
        find probabilty of sequence with prob_of_sequence()
        """
        mc = UBSMarkovChain(
            training_sequence_lst=TestMCStateless.sequence_lst,
            model_output_filename=TestMCStateless.model_file,
        )
        prob = str(
            UBSMarkovChain.s_prob_of_sequence(
                mc.training_model, TestMCStateless.unknown_seq, log_prob=True
            )
        )
        self.assertTrue(
            prob.startswith("-24.1470"),
            f"Unexpected prob: {prob}, instead of -24.1470...",
        )

    def test_use_case_2(self):
        """
        train new model from parameters (model) written to file
        find probabilty of sequence with prob_of_sequence() with
        """
        mc = UBSMarkovChain(model=getDictFromJsonGZ(TestMCStateless.model_file))
        prob = str(
            UBSMarkovChain.s_prob_of_sequence(
                mc.training_model, TestMCStateless.unknown_seq, log_prob=True
            )
        )
        self.assertTrue(
            prob.startswith("-24.1470"),
            f"Unexpected prob: {prob}, instead of -24.1470...",
        )

    def test_use_case_3(self):
        """
        use previous model (case 2) to find prob of sequence with an unseen state:
        the unseen state triggers re-generation of transition_matrix, start_dist, and update of states
        but the object containing model is not updated, but so subsequent use of the object uses first old training model states/transition matrix, etc
        """
        mc = UBSMarkovChain(model=getDictFromJsonGZ(TestMCStateless.model_file))

        UBSMarkovChain.s_prob_of_sequence(
            mc.training_model, TestMCStateless.unknown_seq, log_prob=True
        )
        prob = str(
            UBSMarkovChain.s_prob_of_sequence(
                mc.training_model, TestMCStateless.unknown_seq + "X", log_prob=True
            )
        )
        self.assertTrue(
            prob.startswith("-28.8323"),
            f"Unexpected prob: {prob}, instead of -28.8323...",
        )

        #
        # use case 4:
        # use previous model (case 3) to find prob of (first) sequence yields same prob as first sequence since object is stateless over multiple uses
        #
        prob = str(
            UBSMarkovChain.s_prob_of_sequence(
                mc.training_model, TestMCStateless.unknown_seq, log_prob=True
            )
        )
        self.assertTrue(
            prob.startswith("-24.1470"),
            f"Unexpected prob: {prob}, instead of -24.1470...",
        )


if __name__ == "__main__":
    unittest.main()
