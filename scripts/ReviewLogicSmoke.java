import org.vector.politicsmemory.ReviewLogic;
public class ReviewLogicSmoke {
    public static void main(String[] args) {
        long day1=1763049600000L; // arbitrary; next days are explicitly spaced by calendar days
        ReviewLogic.Result a=ReviewLogic.rate(0,"","yes",day1);
        assert a.score==2;
        ReviewLogic.Result sameDay=ReviewLogic.rate(a.score,a.lastYesDay,"yes",day1+5000);
        assert sameDay.score==2;
        ReviewLogic.Result day2=ReviewLogic.rate(sameDay.score,sameDay.lastYesDay,"yes",ReviewLogic.plusDays(day1,1));
        assert day2.score==3;
        assert ReviewLogic.mastered(3,"yes",false);
        assert !ReviewLogic.mastered(3,"fuzzy",false);
        assert !ReviewLogic.mastered(3,"yes",true);
        ReviewLogic.Result day3=ReviewLogic.rate(day2.score,day2.lastYesDay,"yes",ReviewLogic.plusDays(day1,2));
        assert day3.score==4;
        ReviewLogic.Result fuzzy=ReviewLogic.rate(4,day3.lastYesDay,"fuzzy",day3.dueAt);
        assert fuzzy.score==3;
        ReviewLogic.Result no=ReviewLogic.rate(4,day3.lastYesDay,"no",day3.dueAt);
        assert no.score==0&&no.dueAt==day3.dueAt+600000L;
        System.out.println("ReviewLogic smoke PASS");
    }
}
