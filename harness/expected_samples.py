"""Our own results on the 20 course samples, from the reader in this commit.

sha256 identifies each file. digest is a hash of the scored fields and flags our
reader produced, so the harness can check it gets the same results on the copy.
Neither holds a document value or anything from the answer key.
"""

EXPECTED = {
    "sample_01.pdf": {"sha256": "a7b250c13c068390216fecf6126e2e72c1ee4cc7db3864a0b3298991bf25c685", "digest": "c8f050660fd7720b"},
    "sample_02.pdf": {"sha256": "e1efbbade6bc38bcb8fe92ce8835501e5b55ff7c1f3db1233aa709feab294141", "digest": "a2968c916aef2a27"},
    "sample_03.pdf": {"sha256": "3810060959bec9d7b930714cb1951c854d7c339b5836658096d08cf3707b57a8", "digest": "97be1b49172cad1b"},
    "sample_04.pdf": {"sha256": "33ca0edff945c3b21a5de3d9c667f93811cc8ef4eaa71e42d4a16a57a3c60257", "digest": "5bfb0562e4d668d9"},
    "sample_05.pdf": {"sha256": "e016e499d0d1c586d6d7ac021701ac613d904a48b3322f48783e19bd5f006a75", "digest": "7451e2de390f780d"},
    "sample_06.pdf": {"sha256": "6c5d6a700b06c72848f38833947bbb48a55f0bd15278c3282de931a0ce121313", "digest": "895b1866071a13ea"},
    "sample_07.pdf": {"sha256": "1c8e6bad0e950497404870e476bfa34400445ed997d19f17393f32b1887f1697", "digest": "4c684cc271f5dc8d"},
    "sample_08.pdf": {"sha256": "ac031b35740381c07676b9b354c2e7adfa7172137971ad2c69643658a0f266b7", "digest": "b1b9b2924ee3ba04"},
    "sample_09.pdf": {"sha256": "07427bb6a885d40bad9df68a70f335aabf128261074de424b991fd71eeb859af", "digest": "7fad0bc99e1b03e6"},
    "sample_10.pdf": {"sha256": "0a3f11a9a4846c05e5a8bfa31449ab282291a2d97b911f7be9eb3eb2d32429a7", "digest": "2f1a5d4fa8bab8f4"},
    "sample_11.pdf": {"sha256": "70ae41ab7ba289a5628cec554c7ce82f0a179bdbc18417d065efe13566eb60f1", "digest": "b479df000ebe478a"},
    "sample_12.pdf": {"sha256": "d8ab87e26c97e8bae533fc0f66dfb3e11446501470a5989d37d7d68cf73429e4", "digest": "cb85c3a810fd9aff"},
    "sample_13.pdf": {"sha256": "d0f9a814ec8df5bb49e6d198c6e799331f3c356bbc7eeed68d86c4f5b87754f8", "digest": "0742ccdd56a2dd05"},
    "sample_14.pdf": {"sha256": "64a0efa83fa68030e7e283bc4ea9b833d58adcff6212d4462586b3c6df2e6c2b", "digest": "a50d8964d6fdafa1"},
    "sample_15.pdf": {"sha256": "a611efc90e0c3a8b92b76a89b5ab0b88d2bb97a4fe3e3eecc66f01f4a19d8d51", "digest": "8cda70a0c2a1ba0f"},
    "sample_16.pdf": {"sha256": "74df3e14bee34ced8e3246d58d95207ca187bf16ff422577a1e40e96cc3bc001", "digest": "a07c59112164bfcf"},
    "sample_17.pdf": {"sha256": "16aa085a9e5319ec72f5fb4c7d7c9823c9342c8597d84cc4843009630e2dc8b5", "digest": "6b4b6cfe9fdf7a03"},
    "sample_18.pdf": {"sha256": "05eadb6b3e3490e5d05cc3717fb6f5799bf0db6047aa1d1f71dfbb0a8ee40ce5", "digest": "bcc823d1550cf044"},
    "sample_19.pdf": {"sha256": "df5c64c9d0c0841cb980a271e7c631341c299e2aee142b01b8785d2a7757945e", "digest": "2d7b141bd7d783d5"},
    "sample_20.pdf": {"sha256": "64a47dca8fe0078a8fae792eed47051a6ba0dbd24c41d6237220f55339997e84", "digest": "815a79a473187b4b"},
}
