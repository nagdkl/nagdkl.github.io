from __future__ import annotations
import base64, dataclasses, fcntl, hashlib, importlib.util, json, lzma, os, re, selectors, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
from typing import NoReturn, Sequence
REPOSITORY="nagdkl/nagdkl.github.io"
REPO_URL="https://github.com/nagdkl/nagdkl.github.io.git"
MAIN="0271aa210b587e53c08264de3342ba0fd14bb80f"
MAIN_TREE="285dd06e2192ee1bef33d61f18fcb81917f64ebb"
BRANCH="prompt/pr5-evidence-currentness-v1-20260905"
OLD_HEAD="45a42a76738020ecfb91aba1a1cafc9c1d70ffc3"
PR=7
OLD_SONAR=101395442062
RUNNER="scripts/human_node/repair_pr7_sonar_gate_v5.py"
RESEARCH="docs/research/2026-09-06_pr7-sonar-repair-v5.yaml"
TEST="tests/validation/test_repair_pr7_sonar_gate_v5.py"
FOLLOWUP="scripts/human_node/repair_pr7_sonar_followup_v6.py"
WRITE_SET=(RUNNER,RESEARCH,TEST,FOLLOWUP)
RUNNER_PREIMAGE="5a9578d1faf3f5c08f2ba04e75ba1a8225c0d57a"
RESEARCH_PREIMAGE="6bbea3cd9934b686e4870b4413da64c73d7852b8"
RUNNER_CANDIDATE_SHA256="7037417f7ddae5982599852920076b1419d7a87c03eba8248fadd57cc48ed07f"
PAYLOAD_COMPRESSED_SHA256='5579e27afb2dcb389f329d5e8d4e47c1e66724cba91ea06b322674c6287506a8'
PAYLOAD_COMPRESSED_BYTES=6892
SELF_SOURCE_RESEARCH=r'''
launcher_self_source_recovery_v6_1:
  observed_blocker: NameError_CANONICAL_SOURCE_before_materialization
  remote_mutation_from_failed_attempt: false
  root_cause: compact_followup_called_undefined_self_source_symbol
  corrected_contract:
    - canonical_source_reads_exact_current_launcher_via___file__
    - symlink_or_non_regular_launcher_fails_closed
    - exact_self_source_is_persisted_to_Git_followup_path
    - research_replay_marker_matches_actual_payload_key
  sandbox_evidence:
    self_source_exact_bytes: PASS
    symlink_fail_closed: PASS
    exact_four_path_materialization: PASS
    focused_hostile_tests: 10/10_PASS
    max_heuristic_decision_count: 10
'''
PAYLOAD_B85='{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;CiJRtX%*-h=_*M*W3y&MxMT2sNQc?A8lmijQuO0gGwCmVQZ!Pj_Z#%hBnK?AT|X*^RiH!Mr#sd<hs&7r_Ey1DZ%|=-UG~HFjLfqyf((a`^p>J)B!pm0J6|stl_(iYAA)-sveX)(czn7oif$pb3ME;KWV;Pr^Xp8Wt&?w+2+1J$f0S-Q|RATpsH^%{3hqD!sg}re29>lCvq!N5OAV~dvG9Ff<q{0Z+A}`_mF@Bi7uz+fD-y26Zx|UGQ#96_`zAQw4KZVaTy><!5+6t>|QQX>f!tv<fkR><gM~0%Zz<U!;mTi<&oP;Ncku^SAyEAqt)V9k|J>$lN^3LK}&j&e^;g6G9U7Vz97>XCzDg60(=7;Ud3CdHDavPe!uhaIb$jG8=^#YhDzbBA?xcHnL!LD$s6`z?kF<Rgl1=AX}f@pjEX!OLp?s_H-$+!dg&dpnbTcLR^z0K0&SJm-=+!F$2l~J+%FDfi%va-`F%26ywM4ze6Dd}eJT}}jX_Or=hgBBIxxSngnhwp&|!D-!NgD^4kJ7Dano@jly)_x0=^;p&@DSy|5tx@)1WrMNcFR?@^`sMhLC1tPkY$L$?4^lSV@o{V#}=Hkpk3KOiX#?!mtS?MIs+vKgK(^yL(iCo!mnU5)blF7Eo#HmHa}7wq@fpB0m`D<%WI;KIAP8n`BaAXu9&;B_?-)&`342u;D~PvgTUzy#EI8c%jpCa7N+V5SoydkZTb5&8!#)5}S_w{LmlZ2TE4!b2E4q{uKwIXcb43o+c-fea=Et{pcX7SL}2KVySfRq^z@vTg}-wUwI+U7%${gY28A7e6F4S-uW(TWJ)sOroJPQfOz0084-gkQ1roW@|Jbes!DUhEWyyAW6*49+9hsnTDchfw54>Es!+FxPj;tK=_&8ullPdL_!dIo{98*FdoY#s5sr9B|ItYw;{)5p;j{`*mN|Ox`jdSQls%;-;NQ*$K_huea;+TaWF-|^5JVi#d5^3OOoA~~fG%JCJv(YgWciSVKc)<=eG}b+tw7|}upFg33akv|gy(y(!=^FajvfV{mc8}DlDplLd5W$LZ-kjnD+jkG0$cA#-#gzuvIXCIkc2>v{5rt!#F%>BXYcaP&asa}af;W=h-bBXJCeZZw%*pgZ*+nQ`hJh%YuEnc9)^sOW_PAXZT0FrNdy$ZLlUL^05?+Se>$rI!fZvj?4}gyvJZnJf$njS48`J(SXyzeO(sNyBqtM8zjTou`pe_pS-LYvYE1zsh|eFg#xWN*yu<U#TkZ(3kkfAIxfQQLqi5$wM<n$AV4^-i7_QbGmbfDimT5_@u>_!?vsS#vy!j?j0T!`DJtU2b@}-#5qMss1g-OV6Jq`iCkbrP)19L_K%(e~qH_w|-iRdoezo*-yqcdp%hoiCkaU$FfsW{IG^1^SSdPNqPfQ8);-EWC7kl;X%V1TAsq<v5u2}(ouRML{}j7hEMf{F;2>F;p8JsTh>n$~3R&DC1XjD>4V;1n==Vc8&xxLpckPt{1XFR0+lXEJ^1Hvd@G<1o{-opQNDMG~fF3MUcfUzgal#@sHxMcVtl9$8)9e&+G6DHaMX>T*dOZCf1P_uYlwnx>{C=5S#^F_7cif4`6M-%k`-0rI_3O<F8l{PUAMz0Viz?_s6hg=ML5oiF34sY3on9Av5YZXn(@yzs}YE}TZK&sWA+2Q6Ytn-G@ps#P4cQEM@a+c-KwvjqT<egJ~7;N7mo?<`s`;6Jjv82UK36J04@@{^oqxbOT8U(&;3fo6x{wnmOt?<!ef&Kwe!hN?1WGK_%BY*Iq!d%2UNVVWeVgF0Cj#hwGuF|SFBMw@H6WmU#@nBCE(rR};uj7X(H{3?d5PP1UUHOexOP?cni31EuI6LDtHP<3pJt(NRkm8U#p018U4VnUiVNuorvX_LV^G1G_r1!B})UnKM??U8vq9(JgS{LC~~DHK2kaf};%bpM<;uGs<T6q}aN=T7F26paIKOTO}B!0{Z2e-jeijYO#i%rTY*_EfBuW0f1qQ_%Amp-vkv+A(c)dG~dR3&@?Pvq9`y3BBHF25HQaDr9L~OWEUZ`IzUuK<;oonmzF4<Akd80LreKWt&WKQ7rA?``VlxQ1K^;#;p8+7I;YZ)A?E|gwGj*rhqmp)p!wUDAAej>Te#5KBp%7U_q?8UscKAcKS(gG{~mMdG}fZ4`>`h$vLOpq1^@$X=A0J)07`<pb#Fr%q@JElW!KDyCyb+ODT+Ck3?p~S;<FhT&h_{8F_Fy>N%(0-w;qYybk<~jDZwtabmMc@J})e4Le<LvaF1(PN$vGQ|f+?{jo(#LpK(HnD+C}CQg=WyHUZY#?x^cWlcCz3dRJ+4>hPSb9%0z$$;R6i6z7VYJ$9$7YVUZL3wZBL}!ElePOyln1z8=(H*-fk99P;_?U2cm0jC&KwVcBlxfpLmx5n+ks3=W5vwn=bCJx^opV6(N~6i-8P_^@Z&`ClhBb{3`|Y%X_Q|lI=Rw0_Zk@Vd18-Q%9w#PObE1~9pKq_kcqmTXn0l~7Zt~5%My@ERpte0$4`jT<-I$MN>gs5({;HG7%r{G-MLwskJ>C)+bLFI-O(4>_hj%bEQ3`8KWU+^Z2=E{oea#!xicgLnYme8ceQlE79wi_;<jTu~ztam*#xh*cdCzX1I4AD(*!|zsgmAiq^aqeM!FfPD*m&Uh0;sO#gj-vsYEPnffZauelR-5{EqWK3-P}YEA#yGEnuNc9E5Fr_c?A%6f|dtK5_t0(vgMX4`J>1&ehhEy?4&l6)MSmINjoe&wj8i6LQW)dhKb`dzr5R0Lk(H6Ja#|vI#uh*kZ`$ItqjsS#07&ZIJB9-Pe0oH_nOgBjw!|bb_qg+bX#r_`Vn=!BVwlJ!(&#zil<2Er|AB%AG>Zr_-+A)P2sg>=%R2%sOARcRoBSB)#@DCgILoM{h^4aY_2LFmL~qsqJTZTUm&1NW2zHc33^wT?qe}<6aXCWY1>9)V1pKlYOhnZ1}H~(p_*ieLK@lrt(uF)1d2{WOVdwXTIKGNk~AL*L+=5%jUb`Izc{#qL?OOIjv3oewJKucA7OB{s@|GXF!E%5=05VrqsaG=nn}%=d&`eK%3vG1%ZEgt@`N?d(c`Q939#?(ksqY$(b$`*4&AFy`-~zJz%-^I!H0cu2O8#2LVLP9mBtZJGF~ChnlQ4FmHzZ-OUdTeG~X~VA-5v`!|D;<`%3pFhCqRSgl(j*bO&636)nItw&V>)t_je6AXV(Q(b%6G{s#I=jmjoNlcFv**oOadZAGlLK9r;kzsr#jr?ChSp(Nut4mzp6$ru<0rR#-%Oil!q0(aXk%VZasmFd#ZgX48@zk0ophjpBx^3L%ayi0Nk%OnyH%5s8%Tj2QCWE(+8vDhPQ24DC&2#*Hl&f^YSu7~T0$;VziqfRHplnHRvKB|(oRI)8KH(Zh`RU}4O_^%_b7iKY&&7aqOp=zd0<<lJ;Hq!a%AuA;inkG3H;cMEIiG|TfC;!F@pA%(dp@HLk6cX^cS0FXeLf1AG=2S(oK7z-Glm-EudIIl<n}gdkcehwo0C@E4ZYuxI@QjBN`3<2@yZC0@<GV(e=(OF_T7sk&H-fnqF8=+B7Aik-4#VOhTKz}cI$|NLr~tD_x9U%=+yo>W7ZYGu5#P3oMfbD=F0&iPo($|PgikBzDa0!FEQ*9arxq7gy~zaw8?ts#sF_qMnya&3V?AF6FNU+XM>P2f5VE<w6?O5;mOz1vf21+|cRBX*wK{11tO)<v2>}q@q4|^*?5>~i1=&Kx>cIEfsSziz6SozQPv!0C<AgugB?A_{3^<9bL61JhBT}`RFi-S&OwG|krRf8Pw(-pPO72{ncDW31<Nu^q6~K!muLflN7XAYDEBE1`q(ryW&UwF5asMpk*ESGEuv~fO*4*C5{Z}Trj$l3|YydpFu<y&AyW_WFWL9N-<E%@|K{Q;gV~iPpDJUX)7=6t12SN*C`bZ@X6x-R03wo3oK~m6zE8S-9;VZB_u`Q*g%`W!fkurNteTaD}nS6eIp=n90-dP*T7u*E(@@7SvynAcFdl!^O`B!Iz^m1wNsuo=uxo+inbzY`?@v?-uGuUAu?{?@*yKRe1)#J7qSkJA0!ZU|A`qhAv_6q5_uo*bGgj{-d;9`5;6G#FN1hg~qUorZ;4<oGYZ^_r-#uy^o*#(|3Ga@%%xe&`j&9sMHkY^bjPS7;Wp?0Yjst3WkH`CAnw7*y44|+7ZsTo2#pj%noep}fdFUF;tH`W<lDW*u;D07pHj<rNQDgL73qR%C#%3<-DGY|Nkkw*b5nN;^x13J`K`H|a<wlALc!3_P7!%oO9xv7REoWty}f5Rd3ZQN;}7+dqTuJyzcvhV(#*$X?{N>15C%WOwceqQq4*D)D&vQ(DbnCmXS@J|FqML50fAp|3uTwgE-kv&8Ps+>gWU4x`Q9-eKXY5^Bp(S{hZoE>Ga{Q_&YYUykBSJW_96Ka4-26~55wi<q|SPKlz6{8?RW9wj|$~Nt-z^X~HJH;wnLBHy40$vtaW|AVgh9HA}UANj8JCcylc$_H4-@1Rqpn1m$4{sRLzouJ{sR4rc^ajI`d#CJ+4uGzh0Ng`C?f!$i5BI4;6|T)NjGgmJdyIes7FNNVdJfmJomP{p#bmn9MWX6}7hTtzG(eQ*VVS{u$uv(mY^OfJlzz`R3$8GB#rd$1K;`|Oqe^C;J>em*1II&7M=$H}N71#5pz3PavYD~x0C9eZGN?TB1?G5S-2-qCT(n;B5pV115(FgWn!|4WV3>8AM>tyN%St%!fC1Dte9ZpkzHYOfBny5Ddbwsj*LZ0z9$3LwTA?`~mkV&(7;}2Q3kpI%^LZ=Cku|tGAxY;}TFQbiV-5*SNi!P8v-52J88K2hsc`GUaL%cgABnrJ+CQc#;_7p1%q4!-6U{9b#EKg<V!*4h`8NdC3iKq3ZzD77#A&+8c70knQQaZy7JOhWnHu($hegRNF}j@{GTO-_sVPD(9V{@zcUeAH42TH{>(~ugH<xlAp*lIoB3I%Zg@ETJ_gLarcbiE0ao?1d_(Y0AqW+Iyav4Eyq)|4jD8>p!qXiCfpzNE6!)fS@jjmf+wsYM_o#42SmhvIks^lgOOmI5e2c;f@n28CtcB=mwA-P6QYA^9px^n#F^aO7*{!AVsq%Fx&XJPa#@R2MFk-Q|5u_TIEK)Gy`#z3fm&RNuqF{fzv?6`2mYlzXUt)EBk3^mUy(7<@^y3ZdK5=kDnURlbDU)qy+*{qtWX{7AIA2mxLG&XmC%R((fp^;P?G4N;9R-(z2As?1g!sY$DR&oL{gSwo&*?SDO2ZDbhLB9eHr(z528o)WhaH|Kz`LIa|xGeYdc|V_G-C1jTT?<u&v}LqiWeP|f=LE?KTLxay82YZprGD~l4&i1<{Ks7z-2j@HLiDQ8P(zk^^2vQ!$k62+%SI_BcWM+P&fGrhnU&(^Tt3?!C})8<Mt?hXYix$<yNm{M-jO-H!x0dOS)u0Mp1#L>#1L}8pO;bZ$29#`wg?MWDjqfA8ttM42sQwdW|R^$zKLQD`mBj`;@<-~Zp3EngS+RKrfQU4b+nxzi7(S1Ryc*aQEwU5$ixC@3rIr7UMlaZ9QhYE_+pik@QH&2sUmGO0YQA@5$1f)9ODz~=52?-Qod3#Y_Q72p@6A3wr)L1)VQuC4`<II^AXn)H8P#kKNSG7Wf9<PHj!&bx{>mhA<mhGW%w3_BTLb?F|QyMnfdUiW*g~V;S~s6sjMkI<<&FB+Z;yV!JiK3MJjExZyI~lx)m#l+Z0`ZxJ_u2ekI!*X^z0wfS$Hu*6D>0y62BGZU5`-&Y#L_&r2x(KQWO{ve}?k8>&&{7iXbZ=7`S7lGGx-+JPl6c0`nT1F}b}yualkqryPm9+>-wkHzxpr;11It)-~H21m@s{RdTXsEQ+ERLnHiOwpR)fqs1xNWfoEE*t+(IQsU9eg&0TOuYaoc=8Ux<s<(b@QfL+*G6a%vCoPjRVZd_p%aS;oLRgxKmM?AUAvSJ8fhInYUia}0#3GHNB~Pz-#JTrHhk~sO4E-IS54rOe^v`ThZk`lomj)X-v8Y$oZzrqiW`h+uJFg*LxOt{VmEAmMWpKu+`01O2MbavHh)QBDf3=HS8^38&cxl+=kuuw4@vdCS2CAv&f7oC?FFVtbL(kD{iPrSjrn~T>_=2~v5X68CldWnB5<Y^<+lZI=P$=sZQ%t3f{(51s-J(eTQrYiMI}UdWh~GoIj8to9=h%6+wl(oH0fp&#++j(Bv^1-M07lE2@yzm&c!{K*^n6p425m+sUub`bCNsn73$woiE7~^!~1q%He0+QTI6#N!;B$mk`OPS5#vFidY@2EKDM|^HS#|CyN7sQj*v3T1KV9LCETu$elA>)%Hh5b#HXjqBgjKnUrrhdjIF~q53!N5XtAXCZ+}eERTt%|Nd%jPDL~L<f+jKwN_X6>a*k`F5Lr`4!7ByOIj-d(<+Twaqyu}O+<-L;>h#c3s=6aDCY1$NsurMqtn@m~<aJItgi;|dAaC}U=Lm;hIQ4swCQ7XeFSKkAmdjPpwd4OZTqYJ|-~zw1`$m{WVM1e|;8O1MTMVw242zJJ2Na|x7dk%{Daq6Iw=Zsi$q0ouA^x<>Q_PMFm8IqDMC$-Kh~FY{Sd}7KYFOdrpW~dv-3~7@Bfl}&Iq2_A!%HidPHF8->Kg^9R@Eu}bAZu+G}vCE$pH-x5ZB(0C?KqgGMcuh-^?sAb}{Oy=~uK=A|MPtYAWJqt)mw{vG&%`V9h(^pt3*AbihHuWl)b3EKPl(Y#SW^fKf?UgR37W*Zl#Qlm-N00|QuP9u7z_;S<lv4m;t;C<eC13$A#!8Mlq}`bn#Nw%E2G2xgjaf@QZD+j<0X$S&tyh==nmh3yH-`vGOn<g1z=B(#uv^9-<NeZa$!i8|o}Ww>Txut?G&ONJM;Oh;F@*h%<G_D}gvQhc?JgIW7gpJ~<v^4Bn@F+cTF<WsPiZN40|n2%(8j8rSFmTRMO*<??kCN(wj(ms3=tC}Kx{C^=fhoFoy<2);!TDyU!+r$JQrL?V<ym;?oIZqHnD<ta+vOlw_Nfbx7Dnz%C!P!6*%n5sRQzI^p$HX6?(zN(wq2+D);xXhyLf4{1E|{f=p3Ku$?&^3jaWWsr5zLUok@(z6V%vmfxN88G^~&=acodinas67F=-s*I*%7$g$KMjz6{;e5$cPi*%?1^6*#btUJ4O=rw&v-4A6=juTxaIUFbnaPwZg%*OC4_Zr@4spP_WZjcBbKyqG;5A013f%DtbTgI<nUB$L*Nsp>g>X*$r?q0b0DeYKtGJ$wbX<>D;Gg!{Y;T5~l)dUi)gdnjViK8FeIh;Wc1D!ff79G@o(0WgV)-WuOzgf$f&kJ;6x<aJs8d*UrPE3Lt?P12b9ZzQqV3b7uwqKvN=Rl1Glf69om6Qqu8!fL(+Z_F{tYtwj4{$$2X<Vrxbf4%uF@C3C{Im{L(<g|<=9J)~<b-(!VXg5=M5!48>bGt+peTZu=M$Tae2n<L-&G?@$ysErIV%Z2@F{~iDRi(36Nw5;=X)RgzxAk9w@`l(71G!X0RLAv!nKIT$JEaU-yNiE)Rznp=VIRmBl<wkhWGeIgomi_2NKs-~wnruQd2^Ths)2=qXpj$UrgA{ZP9#<QWkiRz%7cC6WMDA=69=ajpXu?r3s;^W@BwpN&?6i7XJ#_NukelQUgoqd(7m^dpt7IHh^8018%Y1P}l4_!oP>t_2e%piX7nnFXzr^N2NOVfcOZP@nuUg1~h0elN<vZpWkc-ZL=Hm@IDGTZZW(NO5ciO|H0GrBfx;DY!{#;-|(Xu#Dr5zlBX3udZo<KEWCNe$1q<BDS!!G;h>nBqNp*AUxU-oz1J+AZa|L>QiK)3`ZY_P90=hzOkPxBNv6ec_o&znzP^U!SmhYx#e&np@~->!13o;Ch&G->(M0sJMa5CLWgM_b5Sm?*=#07mdgZz`dj+VlFYuD<kVpbFDX8k*rmRW)93kOtJ9#!5>~Hsy&+85U5asB4`2@}lE?cfeo03zcX$d(`z#WU(T_$Xp(u<LU~OB5Tp;!n+(!`?8lzoIZ-dttZycEFq)r(}C4h+i&4|QJ?e`If?S!Be?SNoxV9Lp0J5V)O<kbaqs!!$;CsfGy!!FRaPB$8>GlAB-0}z#;j%irbMVe-<%HXa6Wm7+Ik^wgqfMF)r5NIuqe2i;?3T-cuCOax|_e~B0u`?^S47O&NgfAb`k5PtB^3rUA@c@m1hd~@9TG<2H>W_)ST|@sbLABJ!8&Q49sbrV(uAaqM)RqF)V8cPieX7!JHU5VjoqS+qWGbP8uMh#A!i2i*6_XlsU7&A#4XdAFkTy{}VOqJB&W&iPxWkv3VW7rnUuLOL@fSA{ZvpaEl8Z_}b1qgv3#mqFdT~z$r_U7cD@!VLrweKk`ftJjz9kw(DeN0#7J1*^W&fV_-Jj_#DwNz<a4|esFU|kpFR#7>0&pLsGGU6*3b<)WeIjzHMYphheS)9W>tZ$ZKLJtdc<9lylH7(UAjYu-gkPjgWUaW97}7d9rM8E7;?+#zinDVwKu1bXg&ILL)Lb2^ranQ+zo>aHvuqiS`QOz6A3QHFxNK7vP30oGdjFqW@aR79ar4SJF+aF+|5M55Ugb3tt!aAO$kH(FNqYzxN46Cj5pam^t&5H<ocpERSzH9IS?Pu~LrQt$Vo17Yv1EQSm4MlLZ{7&|%c100GD~ru6{;QMo&nvBYQl0ssI200dcD'
MIRROR_REL=Path("synergy/git-mirrors/nagdkl.github.io.git")
STATE=Path.home()/".local/state/synergy-mesh/pr7-sonar-followup-v6"
@dataclasses.dataclass(slots=True)
class Blocked(RuntimeError):
    reason:str; action:str; code:int=78
class Steps:
    def __init__(self,root:Path):self.root=root;root.mkdir(parents=True,exist_ok=True,mode=0o700);self.i=0;self.last=0
    def emit(self,s:str,err=False):
        print(s,file=sys.stderr if err else sys.stdout,flush=True)
        with (self.root/"steps.log").open("a",encoding="utf-8") as f:f.write(s+"\n")
    def start(self,a:str,t:int):self.i+=1;self.emit(f"STEP_START id={self.i} action={a} timeout={t}s retries=0")
    def ok(self,r:str):self.last=self.i;self.emit(f"STEP_OK id={self.i} result={r} last_confirmed={self.last}")
    def stop(self,e:Blocked)->NoReturn:
        self.emit(f"STEP_BLOCKED id={self.i} result={e.reason} last_confirmed={self.last}",True);self.emit(f"STOP reason={e.reason} next_safe_action={e.action} retry_safe=false breadcrumbs={self.root}",True);raise SystemExit(e.code)
def cp(cmd:Sequence[str],cwd:Path|None=None,timeout=30):
    try:return subprocess.run(list(cmd),cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=timeout,env={**os.environ,"GIT_TERMINAL_PROMPT":"0","GH_PROMPT_DISABLED":"1"})
    except subprocess.TimeoutExpired as e:raise Blocked("command_timeout","read_only_outcome_recovery_before_replay",124) from e
    except OSError as e:raise Blocked("command_execution_failed","verify_required_tool") from e
def sha256b(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def gitblob(b:bytes)->str:return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def payload():
    try:c=base64.b85decode(PAYLOAD_B85.encode())
    except Exception as e:raise Blocked("payload_decode_failed","do_not_execute") from e
    if len(c)!=PAYLOAD_COMPRESSED_BYTES or sha256b(c)!=PAYLOAD_COMPRESSED_SHA256:raise Blocked("payload_identity_mismatch","do_not_execute")
    try:o=json.loads(lzma.decompress(c))
    except Exception as e:raise Blocked("payload_decompress_or_json_failed","do_not_execute") from e
    if set(o)!={"diff","test","research"}:raise Blocked("payload_schema_mismatch","do_not_execute")
    return o
def _hunk_start(line:str)->int:
    m=re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",line)
    if not m:raise Blocked("diff_hunk_header_invalid","do_not_execute")
    return int(m.group(1))-1
def _apply_hunk_line(old:list[str],out:list[str],pos:int,line:str)->tuple[int,bool]:
    if line.startswith("\\ No newline"):return pos,True
    tag=line[:1];body=line[1:]
    if tag=="+":out.append(body);return pos,True
    if tag not in {" ","-"}:return pos,False
    if pos>=len(old) or old[pos]!=body:raise Blocked("diff_context_or_delete_mismatch","do_not_execute")
    if tag==" ":out.append(old[pos])
    return pos+1,True
def _consume_hunk(old:list[str],dl:list[str],out:list[str],pos:int,i:int)->tuple[int,int]:
    while i<len(dl) and not dl[i].startswith("@@ "):
        if dl[i].startswith(("--- ","+++ ")):break
        pos,consumed=_apply_hunk_line(old,out,pos,dl[i])
        if not consumed:break
        i+=1
    return pos,i
def apply_unified(original:str,diff:str)->str:
    old=original.splitlines(keepends=True);dl=diff.splitlines(keepends=True);out=[];pos=0;i=0
    while i<len(dl):
        line=dl[i]
        if not line.startswith("@@ "):i+=1;continue
        start=_hunk_start(line)
        if start<pos:raise Blocked("diff_hunk_overlap","do_not_execute")
        out.extend(old[pos:start]);pos=start
        pos,i=_consume_hunk(old,dl,out,pos,i+1)
    out.extend(old[pos:]);return "".join(out)
def git_bare(m:Path,args:Sequence[str],timeout=30):return cp(["git",f"--git-dir={m}",*args],timeout=timeout)
def lock(path:Path):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);f=path.open("a+")
    try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError as e:f.close();raise Blocked("mirror_busy","inspect_other_mirror_owner") from e
    return f
def valid_mirror(m:Path)->bool:
    if not m.is_dir():return False
    b=git_bare(m,["rev-parse","--is-bare-repository"],5);u=git_bare(m,["remote","get-url","origin"],5)
    return b.returncode==0 and b.stdout.strip()=="true" and u.returncode==0 and u.stdout.strip()==REPO_URL
def fetch_refs(m:Path,t:int):
    r=git_bare(m,["fetch","--quiet","--no-tags","--prune","origin","+refs/heads/main:refs/heads/main",f"+refs/heads/{BRANCH}:refs/heads/{BRANCH}"],t)
    if r.returncode:raise Blocked("mirror_fetch_failed","recover_connectivity_then_new_attempt")
def prepare_mirror(cache:Path,steps:Steps):
    m=cache/MIRROR_REL;m.parent.mkdir(parents=True,exist_ok=True,mode=0o700);f=lock(m.parent/"nagdkl.github.io.mirror.lock")
    try:
        if valid_mirror(m):steps.start("refresh_branch_scoped_mirror",90);fetch_refs(m,90);steps.ok("mirror_refresh_PASS");return m,f
        if m.exists():raise Blocked("canonical_mirror_invalid","preserve_and_inspect_invalid_cache")
        staged=Path(tempfile.mkdtemp(prefix=".nagdkl.github.io.git.",dir=m.parent));cp(["git","init","--bare","--quiet",str(staged)],timeout=15)
        if git_bare(staged,["remote","add","origin",REPO_URL],10).returncode:raise Blocked("mirror_remote_add_failed","inspect_staged_mirror")
        steps.start("initialize_branch_scoped_mirror",240);fetch_refs(staged,240)
        if git_bare(staged,["fsck","--connectivity-only","--no-progress"],30).returncode:raise Blocked("mirror_connectivity_failed","preserve_staged_mirror")
        os.replace(staged,m);steps.ok("mirror_init_PASS");return m,f
    except BaseException:f.close();raise
def ref(m:Path,r:str)->str:
    x=git_bare(m,["rev-parse","--verify",r],10)
    if x.returncode:raise Blocked("mirror_ref_missing","read_only_currentness_recovery")
    return x.stdout.strip()
def tree(m:Path,r:str)->str:
    x=git_bare(m,["show","-s","--format=%T",r],10)
    if x.returncode:raise Blocked("mirror_tree_read_failed","read_only_currentness_recovery")
    return x.stdout.strip()
def gh(endpoint:str,t=20):
    g=shutil.which("gh")
    if not g:raise Blocked("gh_missing","restore_GitHub_CLI")
    r=cp([g,"api","--hostname","github.com",endpoint],timeout=t)
    if r.returncode:raise Blocked("gh_read_failed","recover_GitHub_access")
    try:return json.loads(r.stdout)
    except json.JSONDecodeError as e:raise Blocked("gh_json_invalid","read_only_recovery") from e
def verify_remote_tuple(m:Path,steps:Steps):
    if ref(m,"refs/heads/main")!=MAIN:raise Blocked("main_drift","read_only_reconcile_main")
    if tree(m,"refs/heads/main")!=MAIN_TREE:raise Blocked("main_tree_drift","read_only_reconcile_main")
    if ref(m,f"refs/heads/{BRANCH}")!=OLD_HEAD:raise Blocked("branch_drift","read_only_reconcile_PR7")
    pr=gh(f"repos/{REPOSITORY}/pulls/{PR}")
    if not(isinstance(pr,dict) and pr.get("state")=="open" and pr.get("draft") is True and isinstance(pr.get("head"),dict) and pr["head"].get("sha")==OLD_HEAD and isinstance(pr.get("base"),dict) and pr["base"].get("ref")=="main"):raise Blocked("PR7_currentness_drift","read_only_reconcile_PR7")
    cr=gh(f"repos/{REPOSITORY}/commits/{OLD_HEAD}/check-runs");runs=cr.get("check_runs",[]) if isinstance(cr,dict) else []
    ok=any(isinstance(x,dict) and x.get("id")==OLD_SONAR and x.get("head_sha")==OLD_HEAD and x.get("conclusion")=="failure" and int((x.get("output") or {}).get("annotations_count") or 0)==5 for x in runs)
    if not ok:raise Blocked("Sonar_currentness_drift","read_only_reconcile_PR7_Sonar")
    steps.ok("currentness_PASS PR7=OPEN_DRAFT Sonar5=FAIL")
def worktree(m:Path,run:Path)->Path:
    w=run/"worktree";r=git_bare(m,["worktree","add","--detach",str(w),OLD_HEAD],30)
    if r.returncode:raise Blocked("worktree_add_failed","inspect_mirror_worktree_metadata")
    return w
def verify_preimages(w:Path):
    checks=((RUNNER,RUNNER_PREIMAGE),(RESEARCH,RESEARCH_PREIMAGE))
    for rel,exp in checks:
        p=w/rel
        if not p.is_file() or p.is_symlink() or gitblob(p.read_bytes())!=exp:raise Blocked("preimage_drift_"+rel,"read_only_reconcile_PR7")
    for rel in (TEST,FOLLOWUP):
        if (w/rel).exists():raise Blocked("new_path_already_exists_"+rel,"read_only_reconcile_PR7")
def canonical_source()->str:
    p=Path(__file__)
    if p.is_symlink() or not p.is_file():raise Blocked("canonical_source_unsafe","do_not_execute")
    try:return p.read_text(encoding="utf-8")
    except (OSError,UnicodeDecodeError) as e:raise Blocked("canonical_source_read_failed","do_not_execute") from e
def apply_candidate(w:Path,core:str):
    o=payload();p=w/RUNNER;candidate=apply_unified(p.read_text(encoding="utf-8"),o["diff"])
    if sha256b(candidate.encode())!=RUNNER_CANDIDATE_SHA256:raise Blocked("runner_candidate_identity_mismatch","do_not_write")
    compile(candidate,str(p),"exec");p.write_text(candidate,encoding="utf-8")
    rp=w/RESEARCH;s=rp.read_text(encoding="utf-8");marker="sonar_followup_after_commit_45a42a7:"
    if marker in s:raise Blocked("research_followup_already_present","read_only_reconcile_PR7")
    rp.write_text(s.rstrip()+"\n"+o["research"].lstrip()+"\n"+SELF_SOURCE_RESEARCH.lstrip(),encoding="utf-8")
    tp=w/TEST;tp.parent.mkdir(parents=True,exist_ok=True);tp.write_text(o["test"],encoding="utf-8")
    fp=w/FOLLOWUP;fp.parent.mkdir(parents=True,exist_ok=True);fp.write_text(core,encoding="utf-8")
def paths(w:Path)->set[str]:
    a=cp(["git","diff","--name-only"],w,10);b=cp(["git","ls-files","--others","--exclude-standard"],w,10)
    if a.returncode or b.returncode:raise Blocked("write_set_read_failed","inspect_worktree")
    return {x for x in a.stdout.splitlines()+b.stdout.splitlines() if x}
def import_gate(w:Path):
    p=w/RUNNER;s=importlib.util.spec_from_file_location("pr7_gate_v5_v6_candidate",p);mod=importlib.util.module_from_spec(s);sys.modules[s.name]=mod;s.loader.exec_module(mod);return mod
def run_focused_tests(w:Path,steps:Steps):
    steps.start("compile_and_focused_hostile_tests",120)
    for rel in (RUNNER,TEST,FOLLOWUP):compile((w/rel).read_text(encoding="utf-8"),rel,"exec")
    if paths(w)!=set(WRITE_SET):raise Blocked("write_set_drift","discard_worktree_and_reconcile")
    tests=["tests/validation/test_pr5_evidence_currentness_prompt_v1.py","tests/validation/test_publish_pr5_prompt_governance_v1.py",TEST]
    r=cp([sys.executable,"-B","-m","unittest","-v",*tests],w,90)
    if r.returncode:raise Blocked("focused_tests_failed","repair_candidate")
    if cp(["git","diff","--check"],w,10).returncode:raise Blocked("git_diff_check_failed","repair_candidate")
    steps.ok("compile_tests_exact_write_set_PASS")
def security(w:Path,run:Path,cache:Path,steps:Steps):
    gate=import_gate(w);g=gate.prepare_gitleaks(run,cache,steps);steps.start("precommit_gitleaks",60);report=run/"precommit.json";r=gate.gitleaks_run(g,w,report,git_mode=False,timeout=60)
    if r.returncode or gate.report(report):raise Blocked("precommit_gitleaks_failed","do_not_commit")
    steps.ok("precommit_gitleaks_PASS findings=0");return gate,g
def identity(w:Path):
    n=cp(["git","config","user.name"],w,5);e=cp(["git","config","user.email"],w,5);return (n.stdout.strip() if n.returncode==0 and n.stdout.strip() else "nagdkl",e.stdout.strip() if e.returncode==0 and e.stdout.strip() else "194505092+nagdkl@users.noreply.github.com")
def commit_candidate(w:Path,run:Path,gate,g,steps:Steps)->str:
    steps.start("create_followup_commit",30)
    if cp(["git","add","--",*WRITE_SET],w,10).returncode:raise Blocked("git_add_failed","inspect_worktree")
    staged=cp(["git","diff","--cached","--name-only"],w,10)
    if set(staged.stdout.splitlines())!=set(WRITE_SET):raise Blocked("staged_pathset_mismatch","do_not_commit")
    n,e=identity(w);r=cp(["git","-c",f"user.name={n}","-c",f"user.email={e}","commit","-m","fix(sonar): harden reusable PR7 repair runner"],w,20)
    if r.returncode:raise Blocked("local_commit_failed","inspect_worktree")
    head=cp(["git","rev-parse","HEAD"],w,10).stdout.strip();steps.ok("local_commit_PASS sha="+head)
    steps.start("full_history_gitleaks",90);rep=run/"history.json";s=gate.gitleaks_run(g,w,rep,git_mode=True,timeout=90)
    if s.returncode or gate.report(rep):raise Blocked("full_history_gitleaks_failed","do_not_push")
    steps.ok("full_history_gitleaks_PASS findings=0");return head
def remote(branch:str)->str:
    r=cp(["git","ls-remote","--heads",REPO_URL,f"refs/heads/{branch}"],timeout=20)
    if r.returncode or not r.stdout.strip():raise Blocked("remote_ref_read_failed","read_only_reconcile_remote")
    return r.stdout.split()[0]
def push_exact(w:Path,head:str,steps:Steps):
    if remote("main")!=MAIN or remote(BRANCH)!=OLD_HEAD:raise Blocked("prepush_currentness_drift","read_only_reconcile_before_replay")
    steps.start("zero_retry_push",60)
    try:r=cp(["git","push",REPO_URL,f"HEAD:refs/heads/{BRANCH}"],w,60)
    except Blocked as e:
        if e.code!=124:raise
        if remote(BRANCH)==head:steps.ok("push_outcome_recovered_PASS sha="+head);return
        raise Blocked("push_outcome_unknown","read_only_reconcile_before_any_replay",124)
    if r.returncode or remote(BRANCH)!=head:raise Blocked("push_or_readback_failed","read_only_reconcile_before_any_replay")
    steps.ok("remote_branch_exact_readback_PASS sha="+head)
def postpush(head:str,gate,steps:Steps):
    if remote(BRANCH)!=head:raise Blocked("branch_drift_after_checkpoint","read_only_reconcile_PR7")
    if remote("main")!=MAIN:raise Blocked("main_drift_after_branch_checkpoint","keep_branch_checkpoint_and_reconcile_main")
    pr=gh(f"repos/{REPOSITORY}/pulls/{PR}")
    if not(isinstance(pr,dict) and pr.get("state")=="open" and pr.get("draft") is True and isinstance(pr.get("head"),dict) and pr["head"].get("sha")==head and isinstance(pr.get("base"),dict) and pr["base"].get("ref")=="main"):raise Blocked("PR7_postpush_readback_failed","read_only_reconcile_PR7")
    steps.start("Sonar_readback",180)
    try:s=gate.sonar_readback(head,steps)
    except gate.Blocked as e:raise Blocked(e.reason,e.next_action,e.code) from e
    steps.ok("Sonar_"+s);return s
def main():
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700);run=Path(tempfile.mkdtemp(prefix="run.",dir=STATE));os.chmod(run,0o700);steps=Steps(run);steps.emit(f"RESUME last_confirmed=231 state=PR7_Sonar_followup_v6_1_self_source_fix run_dir={run}")
    if sys.version_info<(3,10):steps.stop(Blocked("python_too_old","use_Python_3_10_plus"))
    if shutil.which("git") is None:steps.stop(Blocked("git_missing","install_git"))
    cache=Path(os.environ.get("XDG_CACHE_HOME",Path.home()/".cache"));m=f=w=None
    try:
        with tempfile.TemporaryDirectory(prefix="synergy-pr7-v6-") as td:
            private=Path(td);private.chmod(0o700);m,f=prepare_mirror(cache,steps);steps.start("exact_remote_tuple",30);verify_remote_tuple(m,steps);w=worktree(m,run);verify_preimages(w);steps.start("materialize_exact_v6_write_set",30);apply_candidate(w,canonical_source());steps.ok("materialize_PASS paths=4");run_focused_tests(w,steps);gate,g=security(w,private,cache,steps);head=commit_candidate(w,private,gate,g,steps);push_exact(w,head,steps);sonar=postpush(head,gate,steps);receipt={"schema":"synergy.pr7_sonar_followup_receipt/v1","head":head,"draft":True,"gitleaks":"PASS","sonar":sonar,"write_set":list(WRITE_SET)};(run/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n");steps.emit(f"GATE=PASS COMMIT={head} PR=7 DRAFT=true SONAR={sonar}");steps.emit(f"BREADCRUMBS={run}");return 0
    except Blocked as e:steps.stop(e)
    finally:
        if f is not None:f.close()
if __name__=="__main__":raise SystemExit(main())
